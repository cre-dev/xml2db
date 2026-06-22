"""Command-line interface for xml2db."""
from __future__ import annotations

import argparse
import html as _html
import json
import os
import queue
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from .config import load_config, parse_yaml_config
from .model import DataModel


# ---------------------------------------------------------------------------
# render command
# ---------------------------------------------------------------------------

def cmd_render(args: argparse.Namespace) -> None:
    config = load_config(args.config) if args.config else None
    model = DataModel(
        xsd_file=args.xsd_file,
        short_name=args.short_name,
        model_config=config,
    )
    fmt = args.format
    if fmt == "erd":
        output = model.get_entity_rel_diagram(text_context=False)
    elif fmt == "target-tree":
        output = model.target_tree
    else:
        output = model.source_tree

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
    def __init__(self, xsd_file: str, config_file: Optional[str], short_name: str):
        self.xsd_file = xsd_file
        self.config_file = config_file
        self.short_name = short_name
        self.lock = threading.Lock()
        self.sse_clients: list[queue.Queue] = []

        self.config_yaml = ""
        if config_file and os.path.exists(config_file):
            with open(config_file, encoding="utf-8") as f:
                self.config_yaml = f.read()

        self.erd = ""
        self.build_error = ""
        self.xsd_mtime = self._xsd_mtime()
        self._rebuild()

    def _xsd_mtime(self) -> Optional[float]:
        try:
            return os.path.getmtime(self.xsd_file)
        except OSError:
            return None

    def _rebuild(self) -> None:
        try:
            cfg = parse_yaml_config(self.config_yaml) if self.config_yaml.strip() else None
            model = DataModel(
                xsd_file=self.xsd_file,
                short_name=self.short_name,
                model_config=cfg,
            )
            self.erd = model.get_entity_rel_diagram(text_context=False)
            self.build_error = ""
        except Exception as exc:
            self.build_error = str(exc)

    def apply_yaml(self, text: str) -> tuple[str, str]:
        """Parse + validate YAML text and rebuild ERD. Returns (erd, error)."""
        try:
            cfg = parse_yaml_config(text) if text.strip() else None
            model = DataModel(
                xsd_file=self.xsd_file,
                short_name=self.short_name,
                model_config=cfg,
            )
            erd = model.get_entity_rel_diagram(text_context=False)
            with self.lock:
                self.config_yaml = text
                self.erd = erd
                self.build_error = ""
            return erd, ""
        except Exception as exc:
            return "", str(exc)

    def save_config(self, text: str) -> str:
        """Save YAML text to config file. Returns error string or empty string."""
        if not self.config_file:
            return "No --config file was specified; cannot save."
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                f.write(text)
            with self.lock:
                self.config_yaml = text
            return ""
        except OSError as exc:
            return str(exc)

    def watch_xsd(self) -> None:
        while True:
            time.sleep(1)
            mtime = self._xsd_mtime()
            if mtime is not None and mtime != self.xsd_mtime:
                self.xsd_mtime = mtime
                self._rebuild()
                self._push("reload")

    def _push(self, event: str) -> None:
        with self.lock:
            clients = list(self.sse_clients)
        for q in clients:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass

    def add_sse_client(self, q: queue.Queue) -> None:
        with self.lock:
            self.sse_clients.append(q)

    def remove_sse_client(self, q: queue.Queue) -> None:
        with self.lock:
            try:
                self.sse_clients.remove(q)
            except ValueError:
                pass


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
            elif self.path == "/erd":
                self._json({"erd": state.erd, "error": state.build_error})
            elif self.path == "/events":
                self._sse()
            else:
                self.send_error(404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            if self.path == "/config":
                erd, error = state.apply_yaml(body)
                self._json({"erd": erd, "error": error})
            elif self.path == "/save":
                self._json({"error": state.save_config(body)})
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

        def _sse(self):
            q: queue.Queue = queue.Queue(maxsize=16)
            state.add_sse_client(q)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                while True:
                    try:
                        event = q.get(timeout=25)
                        self.wfile.write(f"event: {event}\ndata:\n\n".encode())
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                state.remove_sse_client(q)

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
  #hdr-file { opacity: .75; }
  #status { margin-left: auto; font-size: 11px; opacity: .65; }
  main { display: flex; flex: 1; overflow: hidden; }
  #left { width: 360px; min-width: 140px; display: flex; flex-direction: column;
          padding: 8px; gap: 6px; border-right: 1px solid #ddd; background: #fff; }
  #editor-label { font-size: 11px; font-weight: 600; color: #666; }
  #editor { flex: 1; font-family: 'Menlo', 'Consolas', monospace; font-size: 12px;
             border: 1px solid #ccc; border-radius: 3px; padding: 6px;
             resize: none; outline: none; }
  #editor:focus { border-color: #4a90e2; box-shadow: 0 0 0 2px #4a90e230; }
  #msg { font-size: 11px; min-height: 14px; white-space: pre-wrap; word-break: break-word; }
  #msg.ok { color: #2a7a2a; }
  #msg.err { color: #c00; }
  #buttons { display: flex; gap: 6px; }
  button { padding: 5px 14px; border: 1px solid transparent; border-radius: 3px;
           cursor: pointer; font-size: 12px; }
  #apply-btn { background: #4a90e2; color: #fff; border-color: #357abd; }
  #apply-btn:hover { background: #357abd; }
  #save-btn { background: #f0f0f0; border-color: #bbb; }
  #save-btn:hover { background: #e0e0e0; }
  #right { flex: 1; overflow: auto; padding: 14px; }
  #right svg { max-width: 100%; }
</style>
</head>
<body>
<header>
  <strong>xml2db</strong>
  <span id="hdr-file">TMPL_HEADER</span>
  <span id="status">ready</span>
</header>
<main>
  <div id="left">
    <div id="editor-label">model_config (YAML)</div>
    <textarea id="editor" spellcheck="false">TMPL_CONFIG_YAML</textarea>
    <div id="msg"></div>
    <div id="buttons">
      <button id="apply-btn">Apply</button>
      <button id="save-btn">TMPL_SAVE_LABEL</button>
    </div>
  </div>
  <div id="right"></div>
</main>
<script>
mermaid.initialize({ startOnLoad: false, theme: 'default' });

const right = document.getElementById('right');
const msg = document.getElementById('msg');
const editor = document.getElementById('editor');
const status = document.getElementById('status');
const hasSaveTarget = TMPL_HAS_SAVE_TARGET;
let counter = 0;

function setMsg(text, isError) {
  msg.textContent = text;
  msg.className = text ? (isError ? 'err' : 'ok') : '';
}

async function renderDiagram(erd) {
  if (!erd) { right.innerHTML = ''; return; }
  const id = 'g' + (++counter);
  try {
    const { svg } = await mermaid.render(id, erd);
    right.innerHTML = svg;
  } catch (e) {
    right.innerHTML = '<pre style="color:#c00;padding:12px">' + String(e) + '</pre>';
  }
}

async function reloadErd() {
  const r = await fetch('/erd');
  const d = await r.json();
  if (d.error) { setMsg(d.error, true); }
  else { setMsg('', false); await renderDiagram(d.erd); }
}

// Initial render
(async () => {
  await renderDiagram(TMPL_INITIAL_ERD);
  const initErr = TMPL_INITIAL_ERROR;
  if (initErr) setMsg(initErr, true);
})();

document.getElementById('apply-btn').addEventListener('click', async () => {
  status.textContent = 'building…';
  try {
    const r = await fetch('/config', {
      method: 'POST', body: editor.value,
      headers: { 'Content-Type': 'text/yaml' }
    });
    const d = await r.json();
    if (d.error) { setMsg(d.error, true); }
    else { setMsg('', false); await renderDiagram(d.erd); }
  } finally {
    status.textContent = 'ready';
  }
});

document.getElementById('save-btn').addEventListener('click', async () => {
  if (!hasSaveTarget) {
    setMsg('No --config file specified; cannot save.', true);
    return;
  }
  const r = await fetch('/save', {
    method: 'POST', body: editor.value,
    headers: { 'Content-Type': 'text/yaml' }
  });
  const d = await r.json();
  if (d.error) { setMsg(d.error, true); }
  else { setMsg('Saved.', false); }
});

const es = new EventSource('/events');
es.addEventListener('reload', async () => {
  status.textContent = 'reloading…';
  await reloadErd();
  status.textContent = 'ready';
});
es.onerror = () => { status.textContent = 'disconnected'; };
</script>
</body>
</html>
"""


def _build_html(state: _State) -> str:
    header = os.path.basename(state.xsd_file)
    if state.config_file:
        header += f" · {os.path.basename(state.config_file)}"
    save_label = "Save to file" if state.config_file else "Save (no file)"
    return (
        _HTML
        .replace("TMPL_TITLE", _html.escape(header))
        .replace("TMPL_HEADER", _html.escape(header))
        .replace("TMPL_CONFIG_YAML", _html.escape(state.config_yaml))
        .replace("TMPL_SAVE_LABEL", _html.escape(save_label))
        .replace("TMPL_HAS_SAVE_TARGET", "true" if state.config_file else "false")
        .replace("TMPL_INITIAL_ERD", json.dumps(state.erd))
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
    )
    if state.build_error:
        print(f"Warning: initial build error: {state.build_error}")

    threading.Thread(target=state.watch_xsd, daemon=True).start()

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

    r = sub.add_parser("render", help="Print ERD or tree representation to stdout or a file")
    r.add_argument("xsd_file", help="Path to the XSD schema file")
    r.add_argument("--config", "-c", metavar="FILE", help="YAML model config file")
    r.add_argument(
        "--format", "-f",
        choices=["erd", "target-tree", "source-tree"],
        default="erd",
        help="Output format (default: erd)",
    )
    r.add_argument("--output", "-o", metavar="FILE", help="Write to file instead of stdout")
    r.add_argument("--short-name", default="DocumentRoot", metavar="NAME",
                   help="Data model short name (default: DocumentRoot)")

    s = sub.add_parser("serve", help="Launch an interactive schema explorer in the browser")
    s.add_argument("xsd_file", help="Path to the XSD schema file")
    s.add_argument("--config", "-c", metavar="FILE",
                   help="YAML model config file (editable and saveable from the browser)")
    s.add_argument("--port", "-p", type=int, default=8765, metavar="PORT",
                   help="HTTP port (default: 8765)")
    s.add_argument("--no-browser", action="store_true",
                   help="Do not open the browser automatically")
    s.add_argument("--short-name", default="DocumentRoot", metavar="NAME",
                   help="Data model short name (default: DocumentRoot)")

    args = parser.parse_args()
    if args.command == "render":
        cmd_render(args)
    else:
        cmd_serve(args)


if __name__ == "__main__":
    main()
