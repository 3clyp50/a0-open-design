import json
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from helpers import files
from usr.plugins.open_design.hooks import LIBRARY, REVISION

PROJECTS = Path(files.get_abs_path("usr/workdir/open_design"))
COLLECTIONS = {"systems": "design-systems", "templates": "design-templates", "skills": "skills"}
MAX_HTML = 2_000_000


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,95}", value):
        raise ValueError("Invalid identifier.")
    return value


def inside(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("A relative file path is required.")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root.resolve()) or resolved == root.resolve():
        raise ValueError("File is outside the workspace.")
    return resolved


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as target:
        json.dump(value, target, ensure_ascii=False, indent=2)
        temporary = Path(target.name)
    temporary.replace(path)


def read_json(path):
    if path.stat().st_size > MAX_HTML:
        raise ValueError("Metadata is too large.")
    return json.loads(path.read_text(encoding="utf-8"))


def metadata(path):
    text = path.read_text(encoding="utf-8")[:32000]
    if text.startswith("---\n"):
        result = yaml.safe_load(text.split("---", 2)[1])
        return result if isinstance(result, dict) else {}
    return {}


def catalog(collection="systems", query=""):
    if collection not in COLLECTIONS or not isinstance(query, str):
        raise ValueError("Choose systems, templates, or skills.")
    root = LIBRARY / COLLECTIONS[collection]
    if not root.is_dir():
        raise RuntimeError("OpenDesign library is missing. Reinstall the plugin from Plugins.")
    results = []
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or directory.is_symlink() or directory.name.startswith("_"):
            continue
        entry = {"id": directory.name, "name": directory.name.replace("-", " ").title(), "colors": []}
        if collection == "systems":
            if not (directory / "DESIGN.md").is_file():
                continue
            manifest = directory / "manifest.json"
            if manifest.is_file():
                data = read_json(manifest)
                entry.update(name=data.get("name", entry["name"]), category=data.get("category", ""))
            tokens = directory / "design-tokens.json"
            if tokens.is_file():
                for token in read_json(tokens).get("tokens", []):
                    color = token.get("value", "")
                    if isinstance(color, str) and re.fullmatch(r"#[0-9a-fA-F]{3,8}", color) and color not in entry["colors"]:
                        entry["colors"].append(color)
                    if len(entry["colors"]) == 6:
                        break
        else:
            skill = directory / "SKILL.md"
            if not skill.is_file():
                continue
            entry["description"] = str(metadata(skill).get("description", ""))[:500]
        if query.lower() in " ".join(str(value) for value in entry.values()).lower():
            results.append(entry)
    return results


def resource(collection, item, path=""):
    if collection not in COLLECTIONS:
        raise ValueError("Unknown collection.")
    root = inside(LIBRARY / COLLECTIONS[collection], identifier(item))
    path = path or ("DESIGN.md" if collection == "systems" else "SKILL.md")
    target = inside(root, path)
    if target.suffix.lower() not in {".md", ".json", ".css", ".html", ".yaml"}:
        raise ValueError("Choose a text resource.")
    if not target.is_file() or target.stat().st_size > 300_000:
        raise ValueError("Resource is missing or exceeds 300 KB.")
    return {"path": str(target), "content": target.read_text(encoding="utf-8")}


def get_project(project_id):
    folder = inside(PROJECTS, identifier(project_id))
    marker = inside(folder, "project.json")
    if not marker.is_file():
        raise ValueError("Project not found.")
    result = read_json(marker)
    result["id"] = project_id
    result["path"] = str(folder)
    result["ready"] = bool(result.get("artifact") and inside(folder, result["artifact"]).is_file())
    return result


def list_projects():
    if not PROJECTS.exists():
        return []
    results = []
    for folder in PROJECTS.iterdir():
        if folder.is_dir() and not folder.is_symlink() and (folder / "project.json").is_file():
            try:
                results.append(get_project(folder.name))
            except (ValueError, OSError):
                continue
    return sorted(results, key=lambda item: item.get("updated_at", ""), reverse=True)


def create_project(title, brief, system="default", template="dashboard"):
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 100:
        raise ValueError("Title must contain 1–100 characters.")
    if not isinstance(brief, str) or not 1 <= len(brief.strip()) <= 12000:
        raise ValueError("Brief must contain 1–12,000 characters.")
    resource("systems", system)
    resource("templates", template)
    project_id = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc).isoformat()
    project = {"id": project_id, "title": title.strip(), "brief": brief.strip(), "system": system, "template": template,
               "created_at": now, "updated_at": now, "artifact": "", "source_revision": REVISION}
    write_json(inside(PROJECTS, project_id) / "project.json", project)
    return get_project(project_id)


def save_artifact(project_id, html):
    if not isinstance(html, str) or not html.strip() or len(html.encode("utf-8")) > MAX_HTML:
        raise ValueError("Provide HTML between 1 byte and 2 MB.")
    project = get_project(project_id)
    folder = inside(PROJECTS, project_id)
    filename = f"design-{uuid.uuid4().hex[:12]}.html"
    target = inside(folder, filename)
    target.write_text(html, encoding="utf-8")
    project.update(artifact=filename, updated_at=datetime.now(timezone.utc).isoformat())
    write_json(inside(folder, "project.json"), project)
    return get_project(project_id)


def handoff(project_id):
    project = get_project(project_id)
    return (
        f"Use the open_design tool to work on project {project_id}.\n"
        f"Title: {project['title']}\nBrief:\n{project['brief']}\n"
        f"Read the {project['system']} design system and the {project['template']} template with open_design action=read. "
        "Read additional token/component resources as needed. Use the selected resources as design guidance, "
        "and adapt any upstream CLI or artifact-tag instructions to this integration. "
        "Create a complete standalone HTML design with embedded CSS and JavaScript; avoid external scripts and remote tracking. "
        "Save using open_design action=save with this project_id and the complete html. "
        "The preview runs in an opaque-origin sandbox; no network fetch, parent access, popups, or form submission. "
        "Make controls accessible and layouts responsive. Return the actual saved result."
    )


def dispatch(action="status", **args):
    if action == "status":
        return {"ready": (LIBRARY / ".a0-revision").is_file(), "revision": REVISION, "projects": list_projects()}
    if action == "catalog":
        return {"items": catalog(args.get("collection", "systems"), args.get("query", ""))}
    if action == "read":
        return resource(args.get("collection", "systems"), args.get("item", ""), args.get("path", ""))
    if action == "create":
        return {"project": create_project(args.get("title", ""), args.get("brief", ""), args.get("system", "default"), args.get("template", "dashboard"))}
    if action == "project":
        return {"project": get_project(args.get("project_id", ""))}
    if action == "save":
        return {"project": save_artifact(args.get("project_id", ""), args.get("html", ""))}
    if action == "handoff":
        from agent import AgentContext
        project = get_project(args.get("project_id", ""))
        context_id = project.get("context_id", "")
        return {"message": handoff(project["id"]), "context_id": context_id if context_id and AgentContext.get(context_id) else ""}
    if action == "attach_chat":
        from agent import AgentContext
        context_id = args.get("context_id", "")
        if not isinstance(context_id, str) or not AgentContext.get(context_id):
            raise ValueError("Chat not found.")
        project = get_project(args.get("project_id", ""))
        project["context_id"] = context_id
        write_json(inside(inside(PROJECTS, project["id"]), "project.json"), project)
        return {"project": project}
    raise ValueError("Unknown OpenDesign action.")
