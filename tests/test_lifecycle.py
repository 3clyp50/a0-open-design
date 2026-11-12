import pytest

from usr.plugins.open_design import hooks


def test_repeated_install_reuses_revision_and_uninstall_preserves_designs(tmp_path, monkeypatch):
    root = tmp_path / "plugin"
    library = root / "_runtime/library"
    library.mkdir(parents=True)
    (library / ".a0-revision").write_text(hooks.REVISION)
    designs = tmp_path / "designs"
    designs.mkdir()
    (designs / "saved.html").write_text("<h1>Keep</h1>")
    monkeypatch.setattr(hooks, "ROOT", root)
    monkeypatch.setattr(hooks, "LIBRARY", library)
    monkeypatch.setattr(hooks.subprocess, "run", lambda *args, **kwargs: pytest.fail("No download on repeat install"))
    hooks.install()
    hooks.install()
    hooks.uninstall()
    hooks.uninstall()
    assert not library.exists()
    assert (designs / "saved.html").read_text() == "<h1>Keep</h1>"
