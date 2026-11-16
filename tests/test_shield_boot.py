"""Start module of the Windows plugin (packaging/claude_plugin/shield_boot.py): one archive unpacked once into a short
cache folder, safe against a kill and against two starts at the same time, nothing on standard output.

The two Windows folder lookups are replaced by a temporary folder (test only). Invented file names only."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

import pytest

BOOT_SRC = Path(__file__).resolve().parents[1] / "packaging" / "claude_plugin" / "shield_boot.py"
MAKE_ZIP = Path(__file__).resolve().parents[1] / "packaging" / "claude_plugin" / "make_pkgs_zip.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


boot = load("shield_boot_under_test", BOOT_SRC)
make_zip = load("make_pkgs_zip_under_test", MAKE_ZIP)


def fake_packages(root: Path, n: int = 120, big: int = 0) -> dict[str, bytes]:
    """A small invented package tree. ``big``: size of one large file (for a kill in the middle of a file)."""
    files: dict[str, bytes] = {}
    for i in range(n):
        files[f"pkg{i % 7}/sub{i % 3}/mod_{i:03d}.py"] = (f"VALUE = {i}\n" * (1 + i % 5)).encode()
    if big:
        files["pkg_big/_native.bin"] = os.urandom(big)
    files["fakeshield/__init__.py"] = b""
    files["fakeshield/tab.py"] = textwrap.dedent('''
        import sys
        import pthmark
        sys.stderr.write("tab ran as %s with %s, pth line ran: %s\\n" % (__name__, sys.argv[1:], pthmark.RAN))
        ''').encode()
    files["lib_extra/pthmark.py"] = b"RAN = False\n"
    files["extra.pth"] = b"# like pywin32.pth\nlib_extra\nimport pthmark; pthmark.RAN = True\n"
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return files


@pytest.fixture
def engine(tmp_path):
    """A plugin engine folder: pkgs.zip + pkgs.id built by the real build helper."""
    pk = tmp_path / "packages"
    files = fake_packages(pk)
    eng = tmp_path / "plugin" / "engine"
    eng.mkdir(parents=True)
    make_zip.build(pk, eng)
    return eng, files


def same_tree(dest: Path, files: dict[str, bytes]) -> bool:
    return all((dest / rel).read_bytes() == data for rel, data in files.items())


def leftovers(dest: Path) -> list[Path]:
    return [p for p in dest.rglob("~*.tmp")]


# ------------------------------------------------------------------------------------------ names and id

@pytest.mark.parametrize("name", ["../evil.txt", "a/../../evil.txt", "/abs/evil.txt", "\\abs\\evil.txt",
                                  "C:/evil.txt", "C:evil.txt", "a\\..\\..\\evil.txt", "..", "a/b:stream", ""])
def test_bad_member_names_are_refused(name):
    with pytest.raises(boot.BootError):
        boot.member_parts(name)


def test_good_member_names():
    assert boot.member_parts("win32/lib/pywintypes.pyc") == ["win32", "lib", "pywintypes.pyc"]
    assert boot.member_parts("./a//b.py") == ["a", "b.py"]


def test_bad_member_name_stops_before_any_write(tmp_path):
    archive = tmp_path / "pkgs.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("good/first.py", "X = 1\n")
        z.writestr("../evil.txt", "no\n")
    dest = tmp_path / "cache" / "engine" / "v-id"
    with pytest.raises(boot.BootError) as e:
        boot.unpack(str(archive), str(dest))
    assert e.value.message == boot.MSG_REINSTALL
    assert not (tmp_path / "cache" / "engine" / "evil.txt").exists() and not (tmp_path / "evil.txt").exists()
    assert not dest.exists() or not any(dest.rglob("*"))
    assert not boot.is_complete(str(dest))


def test_id_file_and_cache_folder(engine, tmp_path, monkeypatch):
    eng, _ = engine
    ident = (eng / "pkgs.id").read_text().strip()
    import hashlib

    assert ident == hashlib.sha256((eng / "pkgs.zip").read_bytes()).hexdigest()[:12]
    monkeypatch.setattr(boot, "local_app_data", lambda: str(tmp_path / "local"))
    assert boot.cache_dir(str(eng)) == str(tmp_path / "local" / "RAGbase Shield" / "engine" / f"{boot.VERSION}-{ident}")
    (eng / "pkgs.id").write_text("not-an-id\n")
    with pytest.raises(boot.BootError):
        boot.archive_id(str(eng))


def test_same_files_give_the_same_archive(tmp_path):
    pk = tmp_path / "p"
    fake_packages(pk)
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    assert make_zip.build(pk, a)[1] == make_zip.build(pk, b)[1]
    assert (a / "pkgs.zip").read_bytes() == (b / "pkgs.zip").read_bytes()
    assert all(i.compress_type == zipfile.ZIP_DEFLATED for i in zipfile.ZipFile(a / "pkgs.zip").infolist())


def test_version_is_the_engine_version():
    import ragbase_shield

    assert boot.VERSION == ragbase_shield.__version__


def test_local_app_data_never_comes_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "planted"))
    monkeypatch.setattr(boot, "known_folder", lambda guid: "")
    monkeypatch.setattr(boot.os, "name", "nt")
    with pytest.raises(boot.BootError):
        boot.local_app_data()
    seen = []
    monkeypatch.setattr(boot, "known_folder", lambda guid: seen.append(guid) or "C:\\Users\\x\\AppData\\Local")
    assert boot.local_app_data() == "C:\\Users\\x\\AppData\\Local"
    assert seen == [boot.FOLDERID_LOCAL_APP_DATA]


# ------------------------------------------------------------------------------------------ unpack

def test_unpack_once_then_the_mark_means_the_archive_is_not_read(engine, tmp_path, monkeypatch):
    eng, files = engine
    dest = tmp_path / "cache"
    n = boot.unpack(str(eng / "pkgs.zip"), str(dest))
    assert n == len(files) and same_tree(dest, files) and boot.is_complete(str(dest)) and not leftovers(dest)
    # the mark is there: the archive is never opened again, even when it is gone or broken
    (eng / "pkgs.zip").write_bytes(b"broken")
    opened = []
    monkeypatch.setattr(zipfile, "ZipFile", lambda *a, **k: opened.append(a) or (_ for _ in ()).throw(OSError()))
    assert boot.unpack(str(eng / "pkgs.zip"), str(dest)) == 0
    (eng / "pkgs.zip").unlink()
    assert boot.unpack(str(eng / "pkgs.zip"), str(dest)) == 0
    assert opened == []


def test_complete_files_are_kept_and_wrong_sizes_are_written_again(engine, tmp_path):
    eng, files = engine
    dest = tmp_path / "cache"
    first, second = sorted(files)[:2]
    (dest / first).parent.mkdir(parents=True)
    (dest / first).write_bytes(b"x" * len(files[first]))  # right size: taken as complete
    (dest / second).parent.mkdir(parents=True, exist_ok=True)
    (dest / second).write_bytes(b"short")  # wrong size: written again
    n = boot.unpack(str(eng / "pkgs.zip"), str(dest))
    assert n == len(files) - 1
    assert (dest / first).read_bytes() == b"x" * len(files[first])
    assert (dest / second).read_bytes() == files[second]


KILL_SCRIPT = textwrap.dedent('''
    import importlib.util, os, shutil, sys
    spec = importlib.util.spec_from_file_location("b", sys.argv[1]); b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    kill_at = int(sys.argv[4]); count = [0]
    real = shutil.copyfileobj
    def copy(src, out, length=0):
        count[0] += 1
        if count[0] == kill_at:  # half of this file, then the process dies at once (no cleanup, no finally)
            data = src.read()
            out.write(data[: len(data) // 2]); out.flush()
            os._exit(9)
        return real(src, out, length)
    shutil.copyfileobj = copy
    b.unpack(sys.argv[2], sys.argv[3])
    ''')


def test_kill_in_the_middle_then_the_next_start_goes_on(tmp_path):
    pk = tmp_path / "packages"
    files = fake_packages(pk, n=60, big=3_000_000)
    eng = tmp_path / "engine"
    eng.mkdir()
    make_zip.build(pk, eng)
    names = [i.filename for i in zipfile.ZipFile(eng / "pkgs.zip").infolist()]
    kill_at = names.index("pkg_big/_native.bin") + 1  # die in the middle of the big file
    script = tmp_path / "kill.py"
    script.write_text(KILL_SCRIPT)
    dest = tmp_path / "cache"
    r = subprocess.run([sys.executable, "-I", str(script), str(BOOT_SRC), str(eng / "pkgs.zip"), str(dest),
                        str(kill_at)], capture_output=True, timeout=120)
    assert r.returncode == 9, r.stderr
    assert not boot.is_complete(str(dest))
    assert not (dest / "pkg_big" / "_native.bin").exists()  # never a half file under its real name
    assert leftovers(dest), "the killed start left its temporary file"
    done_before = sum(1 for rel in files if (dest / rel).is_file())
    assert done_before == kill_at - 1
    n = boot.unpack(str(eng / "pkgs.zip"), str(dest))  # next start
    assert n == len(files) - done_before
    assert same_tree(dest, files) and boot.is_complete(str(dest))


RACE_SCRIPT = textwrap.dedent('''
    import importlib.util, os, sys, time
    spec = importlib.util.spec_from_file_location("b", sys.argv[1]); b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    go = sys.argv[4]
    while not os.path.exists(go):
        time.sleep(0.001)
    n = b.unpack(sys.argv[2], sys.argv[3])
    sys.stderr.write("wrote %d\\n" % n)
    ''')


def test_two_starts_at_the_same_time(tmp_path):
    pk = tmp_path / "packages"
    files = fake_packages(pk, n=600)
    eng = tmp_path / "engine"
    eng.mkdir()
    make_zip.build(pk, eng)
    script = tmp_path / "race.py"
    script.write_text(RACE_SCRIPT)
    dest, go = tmp_path / "cache", tmp_path / "go"
    procs = [subprocess.Popen([sys.executable, "-I", str(script), str(BOOT_SRC), str(eng / "pkgs.zip"), str(dest),
                               str(go)], stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(3)]
    go.write_text("go")
    outs = [p.communicate(timeout=120) for p in procs]
    assert [p.returncode for p in procs] == [0, 0, 0], outs
    assert all(o[0] == b"" for o in outs)
    assert same_tree(dest, files) and boot.is_complete(str(dest)) and not leftovers(dest)
    written = [int(o[1].split()[1]) for o in outs]
    assert len(files) <= sum(written) and all(w <= len(files) for w in written)


def test_a_file_in_use_by_another_start_is_kept(tmp_path, monkeypatch):
    """Windows cannot replace a .pyd that another start already loaded: that file is complete, keep it."""
    target, tmp = tmp_path / "x.pyd", tmp_path / "~1.tmp"
    target.write_bytes(b"12345")
    tmp.write_bytes(b"12345")

    def busy(src, dst):
        raise PermissionError(13, "in use")

    monkeypatch.setattr(boot.os, "replace", busy)
    boot._replace(str(tmp), str(target), 5)
    assert target.read_bytes() == b"12345" and not tmp.exists()


# ------------------------------------------------------------------------------------------ the whole start

MAIN_SCRIPT = textwrap.dedent('''
    import importlib.util, os, shutil, sys
    eng, local = sys.argv[1], sys.argv[2]
    sys.path.insert(0, eng)  # like "." in python314._pth
    import shield_boot as b
    b.local_app_data = lambda: local  # test only: the Windows folder lookup
    b.MODULE = "fakeshield.tab"
    sys.argv = [os.path.join(eng, "shield_boot.py")] + sys.argv[3:]
    b.main()
    ''')


def run_main(eng: Path, local: Path, tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    script = tmp_path / "main.py"
    script.write_text(MAIN_SCRIPT)
    return subprocess.run([sys.executable, "-I", "-B", str(script), str(eng), str(local), *args],
                          capture_output=True, timeout=120, cwd=str(tmp_path))


def snapshot(folder: Path) -> dict:
    return {p.relative_to(folder).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
            for p in folder.rglob("*")}


def test_start_runs_the_engine_with_site_rules_and_nothing_on_stdout(engine, tmp_path):
    eng, files = engine
    (eng / "shield_boot.py").write_bytes(BOOT_SRC.read_bytes())
    before = snapshot(eng.parent)
    local = tmp_path / "local"
    r = run_main(eng, local, tmp_path, "--test-data", "x")
    assert r.returncode == 0, r.stderr
    assert r.stdout == b""
    assert b"tab ran as __main__ with ['--test-data', 'x'], pth line ran: True" in r.stderr
    assert snapshot(eng.parent) == before  # nothing written inside the plugin folder
    ident = (eng / "pkgs.id").read_text().strip()
    dest = local / "RAGbase Shield" / "engine" / f"{boot.VERSION}-{ident}"
    assert same_tree(dest, files) and boot.is_complete(str(dest))
    r2 = run_main(eng, local, tmp_path)  # second start: mark present
    assert r2.returncode == 0 and r2.stdout == b""


@pytest.mark.parametrize("damage", ["id", "archive", "no_local"])
def test_failure_is_one_french_sentence_on_stderr_and_code_1(engine, tmp_path, damage):
    eng, _ = engine
    (eng / "shield_boot.py").write_bytes(BOOT_SRC.read_bytes())
    local = tmp_path / "local"
    if damage == "id":
        (eng / "pkgs.id").write_text("zz\n")
    elif damage == "archive":
        (eng / "pkgs.zip").write_bytes(b"not a zip")
    else:
        local.write_text("a file, not a folder")  # the cache folder cannot be made
    r = run_main(eng, local, tmp_path)
    assert r.returncode == 1 and r.stdout == b""
    err = r.stderr.decode("utf-8").strip()
    assert err in (boot.MSG_REINSTALL, boot.MSG_UNPACK)
    assert "\n" not in err and "Traceback" not in err and str(tmp_path) not in err


def test_systemroot_is_filled_first():
    env: dict = {}
    assert boot.fill_systemroot(env, windows=True, windows_dir=lambda: "C:\\Windows")
    assert env == {"SYSTEMROOT": "C:\\Windows"}
    env = {"SYSTEMROOT": "D:\\Win"}
    assert not boot.fill_systemroot(env, windows=True, windows_dir=lambda: "C:\\Windows")
    assert not boot.fill_systemroot({}, windows=False)
    src = BOOT_SRC.read_text(encoding="utf-8")
    body = src[src.index("def prepare()"):]
    assert body.index("fill_systemroot()") < body.index("unpack(")
    assert "import asyncio" not in src


def test_boot_uses_the_standard_library_only():
    import ast

    tree = ast.parse(BOOT_SRC.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0])
    assert names <= set(sys.stdlib_module_names), names - set(sys.stdlib_module_names)
    assert "print(" not in BOOT_SRC.read_text(encoding="utf-8")
