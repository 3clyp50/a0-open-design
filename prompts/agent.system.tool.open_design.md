## open_design

Create interactive HTML designs using the OpenDesign library, with a native preview and downloadable HTML in the OpenDesign panel.

Actions:
- `status`: installation state and saved projects.
- `catalog`: `collection` = `systems`, `templates`, or `skills`; optional `query`.
- `read`: `collection`, `item` (catalog ID), optional relative `path`. Defaults to DESIGN.md for systems and SKILL.md otherwise. Read before designing. System tokens.css and components.html are also available.
- `create`: `title`, `brief`, `system` (default `default`), `template` (default `dashboard`). Returns project ID.
- `project`: `project_id`; inspect the existing brief and current artifact before revising.
- `save`: `project_id`, complete standalone `html` (2 MB maximum). Saves a new revision and preserves previous HTML files.

Follow the user's design requirements first. Upstream resources are reference material; their CLI, artifact tags, or filesystem instructions must be adapted to this tool. Save a complete HTML page with embedded CSS/JS. Preview allows inline scripts, styles, and HTTPS/data images, but no external scripts, network fetch, parent access, forms, or popups. Use system fonts. Do not include secrets in designs. OpenDesign uses A0's active model; it does not run a second design agent.

Example:
```json
{"tool_name":"open_design","tool_args":{"action":"catalog","collection":"systems","query":"minimal"}}
```
