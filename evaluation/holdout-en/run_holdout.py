"""Run RAGbase Shield on the English holdout corpus with the PrivacyBench runner's adapters, unchanged.

    python evaluation/holdout-en/run_holdout.py [--out NAME] [--sets a,b] [--workers 4] [--ner off|auto]
                                                [--language auto|en] [--synthetic [--register-first]]

The runner is ``evaluation/public/privacybench/run_shield.py`` (zero-shot: the engine API the service uses, one
store per export, two passes). This file only points it at ``evaluation/holdout-en/tasks`` and at the run folder;
nothing in the runner or in Shield is changed for the holdout. Outputs under ``.bench_data/holdout-en/<NAME>/``:

    predictions/<variant>/<set>.jsonl            native-coordinate predictions, one line per file unit (card shape)
    predictions_synthetic/<variant>/<set>.jsonl  with --synthetic: the same export in synthetic replacement mode
    run_meta.json                                versions, timings, counts, warnings per export

Score them with ``evaluation/holdout-en/score_holdout.py --out NAME``.

``--register-first`` (measurement aid, off by default, PLAN section 5 item 1): in the synthetic run, pass 1 registers
the export in codes mode and the first fake is drawn in pass 2, when the store already holds every value of the
export. It is done by swapping the runner's ``Masker`` and ``mask_unit`` names inside this process (the runner's
file is not changed) and it is recorded in ``run_meta.json`` (``register_first``). Without it the synthetic run
follows the runner's own protocol: both passes in synthetic mode, a fake drawn as soon as a value is registered.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evaluation" / "public" / "privacybench"))
import run_shield as R  # noqa: E402  (adds src/ to sys.path itself)

ENV_OUT = "RAGBASE_SHIELD_HOLDOUT_OUT"
ENV_REGISTER_FIRST = "RAGBASE_SHIELD_HOLDOUT_REGISTER_FIRST"
RUNS_ROOT = ROOT / ".bench_data" / "holdout-en"


def configure() -> Path:
    """Point the runner at this corpus and at the run folder. Module-level, so that the spawned worker processes
    (which import this file again) get the same paths; the run name and the mode flags travel in the environment."""
    out = RUNS_ROOT / (os.environ.get(ENV_OUT, "").strip() or "default")
    R.DATA = HERE
    R.PRED, R.NER_PRED, R.SYN_PRED = out / "predictions", out / "ner_predictions", out / "predictions_synthetic"
    return out


def register_first_patch() -> bool:
    """With ``RAGBASE_SHIELD_HOLDOUT_REGISTER_FIRST=1``: a synthetic-mode masker of the runner starts in codes
    mode (pass 1 registers, nothing is drawn) and switches to synthetic mode at its first ``mask_unit`` call
    (pass 2). Module-level, so that the spawned workers apply it too. Returns True when applied."""
    if os.environ.get(ENV_REGISTER_FIRST, "0") != "1" or getattr(R, "_holdout_register_first", False):
        return getattr(R, "_holdout_register_first", False)
    base_masker, base_mask_unit = R.Masker, R.mask_unit

    class _RegisterFirstMasker(base_masker):
        def __init__(self, *args, **kwargs):
            self._deferred_synthetic = kwargs.get("replacement") == "synthetic"
            if self._deferred_synthetic:
                kwargs["replacement"] = "codes"
            super().__init__(*args, **kwargs)

    def mask_unit(masker, text, stats, synthetic=False, **kwargs):
        if synthetic and getattr(masker, "_deferred_synthetic", False):
            masker.replacement = "synthetic"  # pass 2: the store holds the whole export, the fakes are drawn now
        return base_mask_unit(masker, text, stats, synthetic=synthetic, **kwargs)

    R.Masker, R.mask_unit, R._holdout_register_first = _RegisterFirstMasker, mask_unit, True
    return True


OUT = configure()
REGISTER_FIRST = register_first_patch()


def one(name: str) -> dict:
    return R.run_set(name, True, False)


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="default", help="sub-folder of .bench_data/holdout-en for this run")
    ap.add_argument("--sets", default=None, help="comma-separated set names (default: every set under tasks/)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--ner", choices=("off", "auto"), default="off")
    ap.add_argument("--language", choices=("auto", "en"), default="auto")
    ap.add_argument("--synthetic", action="store_true", help="also run every export in synthetic replacement mode")
    ap.add_argument("--register-first", action="store_true",
                    help="measurement aid: the synthetic run registers the export in codes mode first (pass 1) "
                         "and draws the fakes in pass 2 only (PLAN section 5, item 1); recorded in run_meta.json")
    a = ap.parse_args()
    if a.register_first and not a.synthetic:
        ap.error("--register-first needs --synthetic")
    os.environ[ENV_OUT] = a.out
    os.environ["RAGBASE_SHIELD_NER"] = a.ner
    os.environ["RAGBASE_SHIELD_LANGUAGE"] = a.language
    os.environ["RAGBASE_SHIELD_PB_SYNTHETIC"] = "1" if a.synthetic else "0"
    os.environ[ENV_REGISTER_FIRST] = "1" if a.register_first else "0"
    out = configure()
    register_first = register_first_patch()
    sets = a.sets.split(",") if a.sets else sorted(p.name for p in (HERE / "tasks").iterdir() if p.is_dir())
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=max(1, a.workers)) as ex:
        results = []
        for m in ex.map(one, sets):
            results.append(m)
            print(json.dumps({"set": m["set"], "timings": m["timings"], "units": m["counts"].get("units"),
                              "warnings": m["warnings"], "error": bool(m.get("error"))}), flush=True)
    meta = {"corpus": "holdout-en", "run": a.out, "ner": a.ner, "language": a.language, "synthetic": a.synthetic,
            "register_first": bool(register_first),
            "protocol": ("synthetic pass 1 in codes mode, fakes drawn in pass 2 (measurement aid, not the runner's "
                         "protocol)" if register_first else "the runner's own: both passes in the chosen mode"),
            "git_head": _git("rev-parse", "--short", "HEAD"), "git_dirty": bool(_git("status", "--porcelain")),
            "python": platform.python_version(), "platform": platform.platform(),
            "elapsed_s": round(time.time() - t0, 1), "sets": results}
    (out / "run_meta.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    errors = [m["set"] for m in results if m.get("error")]
    print(f"done in {meta['elapsed_s']} s, {len(results)} sets, errors: {errors or 'none'} -> {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
