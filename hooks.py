import shutil
import subprocess
from pathlib import Path

REVISION = "bc06128813c99fa63f5af53ad2c903c27db057f2"
SOURCE = "https://github.com/nexu-io/open-design.git"
ROOT = Path(__file__).resolve().parent
LIBRARY = ROOT / "_runtime" / "library"


def install(**kwargs):
    marker = LIBRARY / ".a0-revision"
    if marker.is_file() and marker.read_text() == REVISION:
        return
    if not shutil.which("git"):
        raise RuntimeError("OpenDesign requires Git in the Agent Zero framework runtime.")
    LIBRARY.parent.mkdir(parents=True, exist_ok=True)
    staging = LIBRARY.with_name("library-install")
    if staging.exists():
        shutil.rmtree(staging)
    try:
        commands = [
            ["git", "init", str(staging)],
            ["git", "-C", str(staging), "remote", "add", "origin", SOURCE],
            ["git", "-C", str(staging), "sparse-checkout", "set", "design-systems", "design-templates", "skills", "craft"],
            ["git", "-C", str(staging), "fetch", "--depth=1", "--filter=blob:none", "origin", REVISION],
            ["git", "-C", str(staging), "checkout", "--detach", "FETCH_HEAD"],
        ]
        for command in commands:
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=600)
        if not (staging / "design-systems" / "default" / "DESIGN.md").is_file():
            raise RuntimeError("OpenDesign library is incomplete.")
        shutil.rmtree(staging / ".git")
        (staging / ".a0-revision").write_text(REVISION)
        if LIBRARY.exists():
            shutil.rmtree(LIBRARY)
        staging.rename(LIBRARY)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def uninstall(**kwargs):
    runtime = ROOT / "_runtime"
    if runtime.exists():
        shutil.rmtree(runtime)
