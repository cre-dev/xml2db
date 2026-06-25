## Done

- SyntaxWarning in mkdocs build: `_HTML = """\` changed to `_HTML = """` (wip commit), then `\s`, `\S`, `\w` inside JS regex literals doubled to `\\s`, `\\S`, `\\w` so Python emits the correct single-backslash sequences in the rendered HTML (Python 3.12+ raises SyntaxWarning for unrecognised escape sequences in regular strings)
- Link warning in model.py docstring: `./#xml2db...` changed to `data_model.md#xml2db...`
- Config options in configuring.md reordered alphabetically under "Model configuration"
- cli.md created with a reference table for all three subcommands (import, render, serve) and their options
- README updated with a CLI section covering serve, import, and render with examples
- ERD tab in the serve explorer: zoom (+/- buttons, mouse wheel) and pan (click-and-drag) added

## Needs testing

- Zoom and pan in the ERD tab (`xml2db serve`): cannot be verified in the current remote environment because the CDN resources (mermaid, CodeMirror from jsdelivr.net) are blocked by the network policy. Needs a local run:
  - `+` / `-` buttons zoom around the viewport centre
  - Mouse wheel zooms at cursor position (point under cursor stays fixed)
  - Click-and-drag pans the diagram
  - Reset button restores scale 1 and origin
  - Zoom/pan preserved when switching away and back to the ERD tab
  - Zoom resets when config changes produce a new ERD
