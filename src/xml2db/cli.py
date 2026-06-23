"""Command-line interface for xml2db."""
from __future__ import annotations

import argparse
import html as _html
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from .config import load_config, parse_yaml_config
from .model import DataModel


# ---------------------------------------------------------------------------
# render command
# ---------------------------------------------------------------------------

def _get_sa_dialect(db_type: str | None):
    """Return a SQLAlchemy dialect instance for DDL compilation, or None for generic."""
    if db_type is None:
        return None
    from sqlalchemy.dialects import postgresql, mssql, mysql
    _map = {
        "postgresql": postgresql,
        "mssql": mssql,
        "mysql": mysql,
        "mariadb": mysql,
    }
    module = _map.get(db_type)
    return module.dialect() if module is not None else None


def cmd_import(args: argparse.Namespace) -> None:
    config = load_config(args.config) if args.config else None
    metadata = dict(kv.split("=", 1) for kv in args.metadata) if args.metadata else None

    model = DataModel(
        xsd_file=args.xsd_file,
        short_name=args.short_name,
        model_config=config,
        connection_string=args.connection_string,
        db_schema=args.db_schema,
    )
    doc = model.parse_xml(
        xml_file=args.xml_file,
        metadata=metadata,
        skip_validation=not args.validate,
        iterparse=not args.no_iterparse,
        recover=args.recover,
    )
    stats = doc.insert_into_target_tables()
    print(
        f"Imported {args.xml_file}: "
        f"{stats.inserted} rows inserted, {stats.existing} rows already existed "
        f"({stats.duration_temp_insert:.2f}s staging, "
        f"{stats.duration_merge:.2f}s merge, "
        f"{stats.duration_cleanup:.2f}s cleanup)"
    )


def cmd_render(args: argparse.Namespace) -> None:
    config = load_config(args.config) if args.config else None
    db_type = getattr(args, "db_type", None)
    model = DataModel(
        xsd_file=args.xsd_file,
        short_name=args.short_name,
        model_config=config,
        db_type=db_type,
    )
    fmt = args.format
    if fmt == "erd":
        output = model.get_entity_rel_diagram(text_context=False)
    elif fmt == "target-tree":
        output = model.target_tree
    elif fmt == "source-tree":
        output = model.source_tree
    else:  # ddl
        sa_dialect = _get_sa_dialect(db_type)
        parts = [str(s.compile(dialect=sa_dialect)) for s in model.get_all_create_table_statements()]
        parts += [str(s.compile(dialect=sa_dialect)) + "\n\n" for s in model.get_all_create_index_statements()]
        output = "".join(parts)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Written to {args.output}")
    else:
        print(output)


# ---------------------------------------------------------------------------
# serve command — shared state
# ---------------------------------------------------------------------------

class _State:
    def __init__(
        self,
        xsd_file: str,
        config_file: Optional[str],
        short_name: str,
        db_type: Optional[str],
    ):
        self.xsd_file = xsd_file
        self.config_file = config_file if config_file else "model_config.yml"
        self.short_name = short_name
        self.db_type = db_type
        self.lock = threading.Lock()

        self.config_yaml = ""
        if config_file and os.path.exists(config_file):
            with open(config_file, encoding="utf-8") as f:
                self.config_yaml = f.read()

        self.outputs: dict = {"erd": "", "target_tree": "", "source_tree": "", "ddl": ""}
        self.build_error = ""
        self._rebuild(self.config_yaml)

    def _rebuild(self, yaml_text: str) -> tuple[dict | None, str]:
        """Build all outputs from yaml_text. On success updates state and returns (outputs, "").
        On failure updates build_error and returns (None, error)."""
        try:
            cfg = parse_yaml_config(yaml_text) if yaml_text.strip() else None
            model = DataModel(
                xsd_file=self.xsd_file,
                short_name=self.short_name,
                model_config=cfg,
                db_type=self.db_type,
            )
            sa_dialect = _get_sa_dialect(self.db_type)
            ddl_parts = [
                str(s.compile(dialect=sa_dialect))
                for s in model.get_all_create_table_statements()
            ]
            ddl_parts += [
                str(s.compile(dialect=sa_dialect)) + "\n\n"
                for s in model.get_all_create_index_statements()
            ]
            outputs = {
                "erd": model.get_entity_rel_diagram(text_context=False),
                "target_tree": model.target_tree,
                "source_tree": model.source_tree,
                "ddl": "".join(ddl_parts),
            }
            with self.lock:
                self.outputs = outputs
                self.build_error = ""
                self.config_yaml = yaml_text
            return outputs, ""
        except Exception as exc:
            error = str(exc)
            with self.lock:
                self.build_error = error
            return None, error

    def apply_yaml(self, text: str) -> tuple[dict, str]:
        """Rebuild from new YAML text. Always returns (current_outputs, error) so the
        browser keeps the last successful output visible when a build fails."""
        self._rebuild(text)
        with self.lock:
            return dict(self.outputs), self.build_error

    def save_config(self, text: str) -> str:
        """Write text to config_file. Returns error string or ""."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                f.write(text)
            return ""
        except OSError as exc:
            return str(exc)


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

def _make_handler(state: _State):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # silence default stderr logging
            pass

        def do_GET(self):
            if self.path == "/":
                self._serve_html()
            else:
                self.send_error(404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            if self.path == "/config":
                outputs, error = state.apply_yaml(body)
                self._json({"outputs": outputs, "error": error})
            elif self.path == "/save":
                error = state.save_config(body)
                self._json({"error": error, "saved_to": state.config_file})
            else:
                self.send_error(404)

        def _json(self, data: dict):
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_html(self):
            body = _build_html(state).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>xml2db — TMPL_TITLE</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; display: flex; flex-direction: column;
         height: 100vh; background: #f7f8fa; }
  header { padding: 6px 14px; background: #1a1a2e; color: #cdd; font-size: 13px;
           display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
  header strong { color: #fff; }
  main { display: flex; flex: 1; overflow: hidden; }
  #left { width: 360px; min-width: 140px; display: flex; flex-direction: column;
          padding: 8px; gap: 6px; border-right: 1px solid #ddd; background: #fff;
          flex-shrink: 0; }
  #editor-label { font-size: 11px; font-weight: 600; color: #666; }
  #editor { flex: 1; font-family: 'Menlo', 'Consolas', monospace; font-size: 12px;
             border: 1px solid #ccc; border-radius: 3px; padding: 6px;
             resize: none; outline: none; }
  #editor:focus { border-color: #4a90e2; box-shadow: 0 0 0 2px #4a90e230; }
  #msg { font-size: 11px; min-height: 14px; white-space: pre-wrap; word-break: break-word; }
  #msg.ok { color: #2a7a2a; }
  #msg.err { color: #c00; }
  #save-btn { padding: 5px 14px; border: 1px solid #bbb; border-radius: 3px;
              cursor: pointer; font-size: 12px; background: #f0f0f0; }
  #save-btn:hover { background: #e0e0e0; }
  #right { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  #tabs { display: flex; gap: 2px; padding: 6px 8px 0; background: #f0f0f4;
          border-bottom: 1px solid #ddd; flex-shrink: 0; }
  .tab { padding: 5px 14px; border: 1px solid #ccc; border-bottom: none;
         border-radius: 3px 3px 0 0; cursor: pointer; font-size: 12px;
         background: #e8e8ee; color: #444; }
  .tab.active { background: #fff; border-color: #ddd; border-bottom-color: #fff;
                margin-bottom: -1px; color: #000; font-weight: 600; }
  #content { flex: 1; overflow: auto; padding: 14px; }
  #content svg { max-width: 100%; }
  #content pre { font-family: 'Menlo', 'Consolas', monospace; font-size: 12px;
                 white-space: pre; line-height: 1.5; }
</style>
</head>
<body>
<header>
  <strong>xml2db</strong>
  <span>TMPL_HEADER</span>
</header>
<main>
  <div id="left">
    <div id="editor-label">model_config (YAML)</div>
    <textarea id="editor" spellcheck="false">TMPL_CONFIG_YAML</textarea>
    <div id="msg"></div>
    <button id="save-btn">Save to TMPL_SAVE_PATH</button>
  </div>
  <div id="right">
    <div id="tabs">
      <button class="tab active" data-tab="erd">ERD</button>
      <button class="tab" data-tab="target_tree">Target tree</button>
      <button class="tab" data-tab="source_tree">Source tree</button>
      <button class="tab" data-tab="ddl">DDL</button>
    </div>
    <div id="content"></div>
  </div>
</main>
<script>
mermaid.initialize({ startOnLoad: false, theme: 'default' });

const editor = document.getElementById('editor');
const msg = document.getElementById('msg');
const contentEl = document.getElementById('content');

let outputs = TMPL_INITIAL_OUTPUTS;
let currentTab = 'erd';
let debounceTimer = null;
let mermaidCounter = 0;

function setMsg(text, isError) {
  msg.textContent = text;
  msg.className = text ? (isError ? 'err' : 'ok') : '';
}

function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

async function renderTab() {
  if (currentTab === 'erd') {
    const erd = (outputs && outputs.erd) || '';
    if (!erd) {
      contentEl.innerHTML = '<p style="color:#999;padding:12px">No ERD available.</p>';
      return;
    }
    try {
      const id = 'g' + (++mermaidCounter);
      const { svg } = await mermaid.render(id, erd);
      contentEl.innerHTML = svg;
    } catch(e) {
      contentEl.innerHTML = '<pre style="color:#c00;padding:12px">' + escapeHtml(String(e)) + '</pre>';
    }
  } else {
    const text = (outputs && outputs[currentTab]) || '';
    contentEl.innerHTML = '<pre>' + escapeHtml(text) + '</pre>';
  }
}

// Tab switching
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentTab = btn.dataset.tab;
    renderTab();
  });
});

// Debounced auto-rebuild on every keystroke
editor.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    try {
      const r = await fetch('/config', {
        method: 'POST',
        body: editor.value,
        headers: { 'Content-Type': 'text/yaml' },
      });
      const d = await r.json();
      outputs = d.outputs;
      if (d.error) {
        setMsg(d.error, true);
      } else {
        setMsg('', false);
        await renderTab();
      }
    } catch(e) {
      setMsg('Network error: ' + String(e), true);
    }
  }, 500);
});

// Save
document.getElementById('save-btn').addEventListener('click', async () => {
  try {
    const r = await fetch('/save', {
      method: 'POST',
      body: editor.value,
      headers: { 'Content-Type': 'text/yaml' },
    });
    const d = await r.json();
    if (d.error) { setMsg(d.error, true); }
    else { setMsg('Saved to ' + d.saved_to, false); }
  } catch(e) {
    setMsg('Network error: ' + String(e), true);
  }
});

// Initial render
(async () => {
  await renderTab();
  const initErr = TMPL_INITIAL_ERROR;
  if (initErr) setMsg(initErr, true);
})();
</script>
</body>
</html>
"""


def _build_html(state: _State) -> str:
    header = os.path.basename(state.xsd_file)
    return (
        _HTML
        .replace("TMPL_TITLE", _html.escape(header))
        .replace("TMPL_HEADER", _html.escape(header))
        .replace("TMPL_CONFIG_YAML", _html.escape(state.config_yaml))
        .replace("TMPL_SAVE_PATH", _html.escape(state.config_file))
        .replace("TMPL_INITIAL_OUTPUTS", json.dumps(state.outputs))
        .replace("TMPL_INITIAL_ERROR", json.dumps(state.build_error))
    )


# ---------------------------------------------------------------------------
# serve command
# ---------------------------------------------------------------------------

def cmd_serve(args: argparse.Namespace) -> None:
    print(f"Loading schema: {args.xsd_file}")
    state = _State(
        xsd_file=args.xsd_file,
        config_file=args.config,
        short_name=args.short_name,
        db_type=getattr(args, "db_type", None),
    )
    if state.build_error:
        print(f"Warning: initial build error: {state.build_error}")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), _make_handler(state))
    url = f"http://127.0.0.1:{args.port}"
    print(f"Serving at {url}  (Ctrl+C to stop)")

    if not args.no_browser:
        threading.Timer(0.4, webbrowser.open, args=[url]).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="xml2db",
        description="xml2db — explore and configure XSD-to-database mappings",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    i = sub.add_parser("import", help="Parse an XML file and load it into a database")
    i.add_argument("xml_file", help="Path to the XML file to import")
    i.add_argument("xsd_file", help="Path to the XSD schema file")
    i.add_argument("--connection-string", "-d", required=True, metavar="DSN",
                   help="SQLAlchemy connection string (e.g. postgresql+psycopg2://user:pw@host/db)")
    i.add_argument("--config", "-c", metavar="FILE", help="YAML model config file")
    i.add_argument("--short-name", default="DocumentRoot", metavar="NAME",
                   help="Data model short name (default: DocumentRoot)")
    i.add_argument("--db-schema", metavar="SCHEMA", default=None,
                   help="Database schema to use")
    i.add_argument("--metadata", "-m", nargs="*", metavar="KEY=VALUE",
                   help="Metadata values for root table metadata_columns (e.g. -m source=file.xml)")
    i.add_argument("--validate", action="store_true",
                   help="Validate the XML against the schema before importing")
    i.add_argument("--no-iterparse", action="store_true",
                   help="Use recursive parser instead of iterparse (higher memory usage)")
    i.add_argument("--recover", action="store_true",
                   help="Attempt to parse malformed XML")

    r = sub.add_parser("render", help="Print ERD, tree or DDL to stdout or a file")
    r.add_argument("xsd_file", help="Path to the XSD schema file")
    r.add_argument("--config", "-c", metavar="FILE", help="YAML model config file")
    r.add_argument(
        "--format", "-f",
        choices=["erd", "target-tree", "source-tree", "ddl"],
        default="erd",
        help="Output format (default: erd)",
    )
    r.add_argument("--output", "-o", metavar="FILE", help="Write to file instead of stdout")
    r.add_argument("--short-name", default="DocumentRoot", metavar="NAME",
                   help="Data model short name (default: DocumentRoot)")
    r.add_argument("--db-type", metavar="BACKEND", default=None,
                   help="Database backend for DDL output (postgresql, mssql, mysql, …)")

    s = sub.add_parser("serve", help="Launch an interactive schema explorer in the browser")
    s.add_argument("xsd_file", help="Path to the XSD schema file")
    s.add_argument("--config", "-c", metavar="FILE",
                   help="YAML model config file (loaded on startup; Save button writes it back)")
    s.add_argument("--port", "-p", type=int, default=8765, metavar="PORT",
                   help="HTTP port (default: 8765)")
    s.add_argument("--no-browser", action="store_true",
                   help="Do not open the browser automatically")
    s.add_argument("--short-name", default="DocumentRoot", metavar="NAME",
                   help="Data model short name (default: DocumentRoot)")
    s.add_argument("--db-type", metavar="BACKEND", default=None,
                   help="Database backend for DDL tab (postgresql, mssql, mysql, …)")

    args = parser.parse_args()
    if args.command == "import":
        cmd_import(args)
    elif args.command == "render":
        cmd_render(args)
    else:
        cmd_serve(args)


if __name__ == "__main__":
    main()
