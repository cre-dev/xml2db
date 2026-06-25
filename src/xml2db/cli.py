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
        sa_dialect = _get_sa_dialect(db_type) if args.db_names else None
        output = model.get_entity_rel_diagram(text_context=False, use_db_names=args.db_names, sa_dialect=sa_dialect)
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
# serve command: shared state
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
        self.schema_info: dict = {}
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
                "erd_db": model.get_entity_rel_diagram(text_context=False, use_db_names=True, sa_dialect=sa_dialect),
                "target_tree": model.target_tree,
                "source_tree": model.source_tree,
                "ddl": "".join(ddl_parts),
            }
            schema_info = {}
            for table in model.tables.values():
                target_fields = sorted(
                    list(table.columns.keys())
                    + list(table.relations_1.keys())
                    + list(table.relations_n.keys())
                )
                source_fields = sorted(set(
                    fn for (tn, fn) in model.fields_transforms
                    if tn == table.type_name
                ))
                schema_info[table.name] = {
                    "target": target_fields,
                    "source": source_fields,
                }
            with self.lock:
                self.outputs = outputs
                self.schema_info = schema_info
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

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>xml2db: TMPL_TITLE</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script type="importmap">
{
  "imports": {
    "codemirror":                    "https://cdn.jsdelivr.net/npm/codemirror@6.0.2/dist/index.js",
    "@codemirror/state":             "https://cdn.jsdelivr.net/npm/@codemirror/state@6.6.0/dist/index.js",
    "@codemirror/view":              "https://cdn.jsdelivr.net/npm/@codemirror/view@6.43.1/dist/index.js",
    "@codemirror/language":          "https://cdn.jsdelivr.net/npm/@codemirror/language@6.12.3/dist/index.js",
    "@codemirror/commands":          "https://cdn.jsdelivr.net/npm/@codemirror/commands@6.10.3/dist/index.js",
    "@codemirror/autocomplete":      "https://cdn.jsdelivr.net/npm/@codemirror/autocomplete@6.20.3/dist/index.js",
    "@codemirror/search":            "https://cdn.jsdelivr.net/npm/@codemirror/search@6.7.1/dist/index.js",
    "@codemirror/lint":              "https://cdn.jsdelivr.net/npm/@codemirror/lint@6.9.7/dist/index.js",
    "@codemirror/lang-yaml":         "https://cdn.jsdelivr.net/npm/@codemirror/lang-yaml@6.1.3/dist/index.js",
    "@lezer/common":                 "https://cdn.jsdelivr.net/npm/@lezer/common@1.5.2/dist/index.js",
    "@lezer/highlight":              "https://cdn.jsdelivr.net/npm/@lezer/highlight@1.2.3/dist/index.js",
    "@lezer/lr":                     "https://cdn.jsdelivr.net/npm/@lezer/lr@1.4.10/dist/index.js",
    "@lezer/yaml":                   "https://cdn.jsdelivr.net/npm/@lezer/yaml@1.0.4/dist/index.js",
    "@marijn/find-cluster-break":    "https://cdn.jsdelivr.net/npm/@marijn/find-cluster-break@1.0.2/src/index.js",
    "crelt":                         "https://cdn.jsdelivr.net/npm/crelt@1.0.6/index.js",
    "style-mod":                     "https://cdn.jsdelivr.net/npm/style-mod@4.1.3/src/style-mod.js",
    "w3c-keyname":                   "https://cdn.jsdelivr.net/npm/w3c-keyname@2.2.8/index.js"
  }
}
</script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; display: flex; flex-direction: column;
         height: 100vh; background: #f7f8fa; }
  header { padding: 6px 14px; background: #1a1a2e; color: #cdd; font-size: 13px;
           display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
  header strong { color: #fff; }
  main { display: flex; flex: 1; overflow: hidden; }
  #left { width: 380px; min-width: 160px; display: flex; flex-direction: column;
          padding: 8px; gap: 6px; border-right: 1px solid #ddd; background: #fff;
          flex-shrink: 0; }
  #editor-label { font-size: 11px; font-weight: 600; color: #666; }
  #editor { flex: 1; border: 1px solid #ccc; border-radius: 3px; overflow: hidden;
            min-height: 0; }
  #editor:focus-within { border-color: #4a90e2; box-shadow: 0 0 0 2px #4a90e230; }
  .cm-editor { height: 100%; font-size: 12px; }
  .cm-scroller { overflow: auto !important; }
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
  #erd-names { display: none; align-items: center; gap: 10px; padding: 4px 14px;
               font-size: 11px; color: #555; border-bottom: 1px solid #eee;
               background: #fafafa; flex-shrink: 0; }
  #erd-names.visible { display: flex; }
  #erd-names label { display: flex; align-items: center; gap: 3px; cursor: pointer; }
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
    <div id="editor"></div>
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
    <div id="erd-names">
      Names &amp; types:
      <label><input type="radio" name="erd_names" value="logical" checked> Logical</label>
      <label><input type="radio" name="erd_names" value="db"> DB</label>
    </div>
    <div id="content"></div>
  </div>
</main>
<script type="module">
import { basicSetup, EditorView } from "codemirror";
import { keymap } from "@codemirror/view";
import { indentWithTab } from "@codemirror/commands";
import { autocompletion, acceptCompletion } from "@codemirror/autocomplete";
import { yaml } from "@codemirror/lang-yaml";

// Schema info injected from server:
// { tableName: { source: [sourceFieldName, ...], target: [targetFieldName, ...] }, ... }
// source = XSD names (used by "transform"); target = post-simplification names (used by "type"/"rename")
const SCHEMA_INFO = TMPL_SCHEMA_INFO_JSON;

// ---- completion knowledge ----
const ROOT_KEYS  = ['as_columnstore','row_numbers','transform','record_hash_column_name',
                    'record_hash_size','metadata_columns','tables'];
const TABLE_KEYS = ['reuse','as_columnstore','choice_transform','extra_args','fields'];
const FIELD_KEYS = ['type','rename','transform'];
const META_KEYS  = ['name','type','nullable','default','server_default','comment','index','unique'];
const INDEX_KEYS = ['name','columns','unique'];
const BOOL_KEYS        = new Set(['reuse','as_columnstore','row_numbers','nullable','unique','index']);
const CHOICE_TRANSFORM = ['auto','true','false'];
const SA_TYPES   = ['String','String(100)','Integer','BigInteger','SmallInteger','Float',
                    'Double','Numeric','Boolean','DateTime','DateTime(timezone=True)',
                    'Date','Time','Text','LargeBinary','JSON','Uuid'];
const TRANSFORMS     = ['auto','false','skip','elevate_wo_prefix'];
const TOP_TRANSFORMS = ['auto','false'];

// Walk backwards from the current line to build the YAML key path at the cursor.
// Uses indent-level heuristic: each time we see a line with smaller indentation
// that looks like a YAML key, we add it to the path.
function getContext(state, pos) {
  const doc = state.doc;
  const curLine = doc.lineAt(pos);
  const trimmed = curLine.text.trimStart();
  const rawIndent = curLine.text.length - trimmed.length;
  const path = [];
  let searchIndent = rawIndent;
  for (let n = curLine.number - 1; n >= 1; n--) {
    if (searchIndent <= 0) break;
    const text = doc.line(n).text;
    const s = text.trimStart();
    if (!s) continue;
    const li = text.length - s.length;
    if (li >= searchIndent) continue;
    // Match optional list marker ("- ") then a key name followed by ":"
    const m = s.match(/^(?:-\\s+)?(\\S[^:#]*?):/);
    if (m) { path.unshift(m[1].trim()); searchIndent = li; }
  }
  return { indent: rawIndent, path };
}

function getKeyCompletions(path) {
  if (path.length === 0) return ROOT_KEYS;
  if (path[0] === 'tables') {
    if (path.length === 1) return Object.keys(SCHEMA_INFO);          // table names
    if (path.length === 2) return TABLE_KEYS;                         // table config keys
    if (path.length === 3 && path[2] === 'fields') {                  // field names
      const info = SCHEMA_INFO[path[1]] || {};
      const targetSet = new Set(info.target || []);
      const sourceSet = new Set(info.source || []);
      const opts = [];
      for (const f of (info.source || [])) {
        const inTarget = targetSet.has(f);
        opts.push({ label: f, type: 'property', detail: inTarget ? undefined : 'source' });
      }
      for (const f of (info.target || [])) {
        if (!sourceSet.has(f))
          opts.push({ label: f, type: 'property', detail: 'target' });
      }
      return opts;
    }
    if (path.length >= 4 && path[2] === 'fields') return FIELD_KEYS; // field config keys
  }
  if (path[0] === 'metadata_columns') return META_KEYS;
  if (path.includes('extra_args'))    return INDEX_KEYS;
  return [];
}

// Detect "key: <cursor>" pattern and return value completions for that key.
function getValueCompletions(state, pos, path) {
  const line = state.doc.lineAt(pos);
  const before = line.text.slice(0, pos - line.from);
  const m = before.match(/(\\w+)\\s*:\\s*$/);
  if (!m) return null;
  const key = m[1];
  if (BOOL_KEYS.has(key))        return ['true','false'].map(v => ({ label: v, type: 'keyword' }));
  if (key === 'choice_transform') return CHOICE_TRANSFORM.map(v => ({ label: v, type: 'keyword' }));
  if (key === 'type')             return SA_TYPES.map(v => ({ label: v, type: 'class' }));
  if (key === 'transform')        return (path.length === 0 ? TOP_TRANSFORMS : TRANSFORMS).map(v => ({ label: v, type: 'keyword' }));
  return null;
}

function xml2dbCompleter(context) {
  const word = context.matchBefore(/\\w*/);
  if (!word || (word.from === word.to && !context.explicit)) return null;
  const { path } = getContext(context.state, context.pos);
  const valueOpts = getValueCompletions(context.state, context.pos, path);
  if (valueOpts) return { from: word.from, options: valueOpts };

  const keys = getKeyCompletions(path);
  if (!keys.length) return null;
  return { from: word.from, options: keys.map(k => typeof k === 'string' ? { label: k, type: 'property' } : k) };
}

// ---- editor setup ----
mermaid.initialize({ startOnLoad: false, theme: 'default' });

const msg        = document.getElementById('msg');
const contentEl  = document.getElementById('content');
const erdNamesEl = document.getElementById('erd-names');
let outputs      = TMPL_INITIAL_OUTPUTS;
let currentTab   = 'erd';
let debounceTimer = null;
let mermaidCounter = 0;

function erdKey() {
  return document.querySelector('input[name="erd_names"]:checked').value === 'db'
    ? 'erd_db' : 'erd';
}

const view = new EditorView({
  doc: TMPL_CONFIG_YAML_JSON,
  extensions: [
    basicSetup,
    yaml(),
    autocompletion({ override: [xml2dbCompleter] }),
    keymap.of([{ key: "Tab", run: acceptCompletion }, indentWithTab]),
    EditorView.updateListener.of(upd => {
      if (!upd.docChanged) return;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => { debounceTimer = null; doRebuild(); }, 500);
    }),
  ],
  parent: document.getElementById('editor'),
});

// ---- UI helpers ----
function setMsg(text, isError) {
  msg.textContent = text;
  msg.className = text ? (isError ? 'err' : 'ok') : '';
}

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function renderTab() {
  if (currentTab === 'erd') {
    erdNamesEl.classList.add('visible');
    const erd = (outputs && outputs[erdKey()]) || '';
    if (!erd) { contentEl.innerHTML = '<p style="color:#999;padding:12px">No ERD available.</p>'; return; }
    try {
      const id = 'g' + (++mermaidCounter);
      const { svg } = await mermaid.render(id, erd);
      contentEl.innerHTML = svg;
    } catch(e) {
      contentEl.innerHTML = '<pre style="color:#c00;padding:12px">' + escapeHtml(String(e)) + '</pre>';
    }
  } else {
    erdNamesEl.classList.remove('visible');
    contentEl.innerHTML = '<pre>' + escapeHtml((outputs && outputs[currentTab]) || '') + '</pre>';
  }
}

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentTab = btn.dataset.tab;
    renderTab();
  });
});

document.querySelectorAll('input[name="erd_names"]').forEach(radio => {
  radio.addEventListener('change', () => { if (currentTab === 'erd') renderTab(); });
});

async function doRebuild() {
  try {
    const r = await fetch('/config', {
      method: 'POST', body: view.state.doc.toString(),
      headers: { 'Content-Type': 'text/yaml' },
    });
    const d = await r.json();
    outputs = d.outputs;
    if (d.error) { setMsg(d.error, true); }
    else { if (!debounceTimer) setMsg('', false); await renderTab(); }
  } catch(e) { setMsg('Network error: ' + String(e), true); }
}

document.getElementById('save-btn').addEventListener('click', async () => {
  try {
    const r = await fetch('/save', {
      method: 'POST', body: view.state.doc.toString(),
      headers: { 'Content-Type': 'text/yaml' },
    });
    const d = await r.json();
    if (d.error) { setMsg(d.error, true); }
    else { setMsg('Saved to ' + d.saved_to, false); }
  } catch(e) { setMsg('Network error: ' + String(e), true); }
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
        .replace("TMPL_SAVE_PATH", _html.escape(state.config_file))
        .replace("TMPL_SCHEMA_INFO_JSON", json.dumps(state.schema_info))
        .replace("TMPL_CONFIG_YAML_JSON", json.dumps(state.config_yaml))
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
        description="xml2db: explore and configure XSD-to-database mappings",
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
    r.add_argument("--db-names", action="store_true",
                   help="Use physical database identifiers in the ERD instead of logical names")

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
