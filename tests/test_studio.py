import json
from pathlib import Path

import pytest
from flask import Flask

from usr.plugins.open_design.helpers import studio
from usr.plugins.open_design.api.artifact import Artifact


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    library = tmp_path / "library"
    system = library / "design-systems/default"
    system.mkdir(parents=True)
    (system / "DESIGN.md").write_text("# A design system")
    (system / "manifest.json").write_text(json.dumps({"name": "Default"}))
    (system / "design-tokens.json").write_text(json.dumps({"tokens": [{"value": "#123456"}, {"value": "url(javascript:bad)"}]}))
    template = library / "design-templates/dashboard"
    template.mkdir(parents=True)
    (template / "SKILL.md").write_text("---\nname: dashboard\ndescription: A dashboard\n---\n# Template")
    monkeypatch.setattr(studio, "LIBRARY", library)
    monkeypatch.setattr(studio, "PROJECTS", tmp_path / "projects")
    return tmp_path


def test_real_catalog_and_resources(workspace):
    assert studio.catalog()[0]["colors"] == ["#123456"]
    assert studio.catalog(query="missing") == []
    assert studio.resource("systems", "default")["content"] == "# A design system"
    assert studio.catalog("templates")[0]["description"] == "A dashboard"


def test_design_revisions_preserve_previous_artifact(workspace):
    project = studio.create_project("Design", "An accessible dashboard")
    assert not project["ready"]
    first = studio.save_artifact(project["id"], "<!doctype html><h1>First</h1>")
    second = studio.save_artifact(project["id"], "<!doctype html><h1>Second</h1>")
    assert first["artifact"] != second["artifact"]
    assert (Path(project["path"]) / first["artifact"]).read_text().endswith("First</h1>")
    assert studio.list_projects()[0]["artifact"] == second["artifact"]
    assert "action=save" in studio.handoff(project["id"])


@pytest.mark.parametrize("value", ["../outside", "/etc/passwd", "a/b", "", None, "--help"])
def test_identifiers_reject_traversal(workspace, value):
    with pytest.raises(ValueError):
        studio.get_project(value)


def test_symlink_and_resource_escape_are_rejected(workspace):
    outside = workspace / "private.md"
    outside.write_text("private")
    (studio.LIBRARY / "design-systems/default/escape.md").symlink_to(outside)
    for path in ("escape.md", "../../private.md", "/etc/passwd"):
        with pytest.raises(ValueError):
            studio.resource("systems", "default", path)


def test_input_limits_and_missing_system(workspace):
    for title, brief, system in [("", "brief", "default"), ("title", "", "default"), ("title", "brief", "absent")]:
        with pytest.raises(ValueError):
            studio.create_project(title, brief, system)
    project = studio.create_project("Title", "Brief")
    with pytest.raises(ValueError):
        studio.save_artifact(project["id"], "x" * (studio.MAX_HTML + 1))


@pytest.mark.asyncio
async def test_preview_auth_sandbox_and_download(workspace, monkeypatch):
    from usr.plugins.open_design.api import artifact
    monkeypatch.setattr(artifact, "PROJECTS", studio.PROJECTS)
    project = studio.create_project("Preview", "Brief")
    studio.save_artifact(project["id"], "<script>parent.document.body.innerHTML='bad'</script>")
    app = Flask(__name__)
    handler = Artifact(app, None)
    assert handler.requires_auth()
    assert handler.get_methods() == ["GET"]
    with app.test_request_context(f"/?id={project['id']}"):
        from flask import request
        response = await handler.process({}, request)
        assert response.status_code == 200
        policy = response.headers["Content-Security-Policy"]
        assert "sandbox allow-scripts" in policy and "allow-same-origin" not in policy
        assert "connect-src 'none'" in policy
        response.close()
    with app.test_request_context(f"/?id={project['id']}&download=1"):
        response = await handler.process({}, request)
        assert "attachment" in response.headers["Content-Disposition"]
        response.close()
