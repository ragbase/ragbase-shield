#!/usr/bin/env bash
# Reproduce the results of one benchmark set: install the tool, run it on the set, score the output.
#
#   bash evaluation/datasets/reproduce.sh SET [MODE]
#
#   SET    ref | max
#   MODE   fast (default) | precise | presidio
#          fast and precise are the two modes of RAGbase Shield 0.4.4; presidio is Microsoft Presidio 2.2.364.
#
# Run it from a clone of https://github.com/ragbase/ragbase-shield, with Python 3.10 or newer and an internet
# connection for the installs. On Windows, use Git Bash or WSL. To choose the Python, set PYTHON to its path:
#
#   PYTHON=/usr/local/bin/python3.12 bash evaluation/datasets/reproduce.sh ref
#
# Shield comes from the release page of the repository: the script downloads the wheel, checks its SHA-256 and
# installs the file.
#
# The virtual environment of each mode, the downloaded wheel, the tool's output and the scores go under
# .bench_data/datasets (ignored by git). The tool itself runs with the network closed.
#
# precise downloads the Shield model once (about 1.25 GB) into RAGBASE_SHIELD_MODELS_DIR
# (default: ~/.ragbase-shield/models). On an Intel Mac, precise needs Python 3.10 to 3.12.
set -euo pipefail

usage() { echo "usage: bash evaluation/datasets/reproduce.sh ref|max [fast|precise|presidio]" >&2; exit 2; }
SET="${1:-}"
MODE="${2:-fast}"
case "$SET" in ref|max) ;; *) usage ;; esac
case "$MODE" in fast|precise|presidio) ;; *) usage ;; esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LAPTOP="$ROOT/evaluation/laptop"
DATA="$ROOT/evaluation/datasets/$SET"
WORK="$ROOT/.bench_data/datasets"
VENV="$WORK/venv-$MODE"
OUT="$WORK/out/$SET-$MODE"
SHIELD="0.4.4"   # the version of the benchmark page
# The wheel of that version on the release page, its SHA-256 (the value of SHA256SUMS on the same page), its copy here.
WHEEL="ragbase_shield-$SHIELD-py3-none-any.whl"
WHEEL_URL="https://github.com/ragbase/ragbase-shield/releases/download/v$SHIELD/$WHEEL"
WHEEL_SHA256="b70d309802890ef5e7da817e9f5c86171eb9ec461441950fd5e3c4287b8f6e9a"
WHEEL_FILE="$WORK/wheels/$WHEEL"
READERS="pdfplumber==0.11.10 pdfminer.six==20260107 openpyxl==3.1.2"

# 1. The files of the set are the published ones.
if command -v sha256sum >/dev/null 2>&1; then SUM="sha256sum"; else SUM="shasum -a 256"; fi
(cd "$DATA" && $SUM -c SHA256SUMS >/dev/null) || { echo "The files of $DATA differ from SHA256SUMS." >&2; exit 1; }

# 2. Install the tool in its own virtual environment.
PYTHON="${PYTHON:-$(command -v python3 || command -v python || true)}"
NEED="Python 3.10 or newer is needed. Set PYTHON to its path, for example:
  PYTHON=/usr/local/bin/python3.12 bash evaluation/datasets/reproduce.sh $SET $MODE"
[ -n "$PYTHON" ] || { echo "$NEED" >&2; exit 1; }
"$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 10))' || { echo "$NEED" >&2; exit 1; }
if [ "$MODE" = precise ]; then   # the model library has no build for an Intel Mac with Python 3.13 or newer
  "$PYTHON" -c 'import platform, sys; sys.exit(sys.platform == "darwin" and platform.machine() == "x86_64" and sys.version_info >= (3, 13))' \
    || { echo "On an Intel Mac, precise needs Python 3.10 to 3.12. Set PYTHON to its path." >&2; exit 1; }
fi
mkdir -p "$WORK"
if [ ! -d "$VENV" ]; then "$PYTHON" -m venv "$VENV"; fi
if [ -d "$VENV/Scripts" ]; then BIN="$VENV/Scripts"; else BIN="$VENV/bin"; fi
PY="$BIN/python"
# Shield comes from the release page: download the wheel once, check its SHA-256, and only then install the file.
shield_checked() {
  "$PY" -c 'import hashlib, sys; sys.exit(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest() != sys.argv[2])' \
    "$WHEEL_FILE" "$WHEEL_SHA256" 2>/dev/null
}
get_shield() {
  if ! shield_checked; then
    rm -f "$WHEEL_FILE"
    "$PY" -m pip download --quiet --no-deps --dest "$WORK/wheels" "$WHEEL_URL" \
      || { echo "The download of $WHEEL_URL failed." >&2; exit 1; }
    shield_checked \
      || { echo "The SHA-256 of $WHEEL_FILE is not the value of the release page. The script stops." >&2; exit 1; }
  fi
  echo "Shield $SHIELD: $WHEEL from the release page, SHA-256 checked."
}
echo "Installing ($MODE). The first run takes a few minutes."
"$PY" -m pip install --quiet --upgrade pip
case "$MODE" in
  fast)
    get_shield
    "$PY" -m pip install --quiet "$WHEEL_FILE" $READERS
    TOOL="Shield $SHIELD Fast" ;;
  precise)
    get_shield
    "$PY" -m pip install --quiet "${WHEEL_FILE}[ner]" $READERS
    export RAGBASE_SHIELD_MODELS_DIR="${RAGBASE_SHIELD_MODELS_DIR:-$HOME/.ragbase-shield/models}"
    case "$("$BIN/ragbase-shield" ner download --dry-run 2>&1 || true)" in
      *"already present"*) ;;
      *) "$BIN/ragbase-shield" ner download || {   # the model, once
           rc=$?
           echo "The model is not there yet. Run this command yourself in a terminal, then run this script again:" >&2
           echo "  RAGBASE_SHIELD_MODELS_DIR=\"$RAGBASE_SHIELD_MODELS_DIR\" \"$BIN/ragbase-shield\" ner download" >&2
           exit $rc; } ;;
    esac
    TOOL="Shield $SHIELD Precise" ;;
  presidio)
    "$PY" -m pip install --quiet "presidio-analyzer==2.2.364" "presidio-anonymizer==2.2.364" "spacy==3.8.16" \
      "thinc==8.3.13" "tldextract==5.4.0" "phonenumbers==9.0.43" $READERS \
      "https://github.com/explosion/spacy-models/releases/download/fr_core_news_md-3.8.0/fr_core_news_md-3.8.0-py3-none-any.whl"
    export TLDEXTRACT_CACHE="$WORK/tldextract-cache"
    "$PY" -c "import tldextract; tldextract.extract('exemple.fr')"   # the list of domain endings, fetched once
    TOOL="Presidio 2.2.364" ;;
esac

# 3. Run the tool on the set (a new output folder for each run).
rm -rf "$OUT"
mkdir -p "$OUT"
echo "Running $TOOL on $SET."
case "$MODE" in
  fast)     "$PY" "$LAPTOP/run_shield_files.py" --set-dir "$DATA" --out "$OUT/output" --mode rules > "$OUT/run.log" 2>&1 ;;
  precise)  "$PY" "$LAPTOP/run_shield_files.py" --set-dir "$DATA" --out "$OUT/output" --mode ner > "$OUT/run.log" 2>&1 ;;
  presidio) "$PY" "$LAPTOP/run_presidio.py" --set-dir "$DATA" --out "$OUT/output" --language fr > "$OUT/run.log" 2>&1 ;;
esac || { tail -n 20 "$OUT/run.log" >&2; exit 1; }

# 4. Score: legal terms changed (score_text.py), then overall score, precision and recall (score_f1.py).
"$PY" "$LAPTOP/score_text.py" score --gold "$DATA/gold.jsonl" --inputs "$DATA/input" --outputs "$OUT/output" \
  --runlog "$OUT/output/runlog.jsonl" --json "$OUT/score_text.json" --md "$OUT/score_text.md" --tool "$TOOL" > /dev/null
"$PY" "$LAPTOP/score_f1.py" score --gold "$DATA/gold.jsonl" --inputs "$DATA/input" --outputs "$OUT/output" \
  --runlog "$OUT/output/runlog.jsonl" --score-text-json "$OUT/score_text.json" --json "$OUT/score_f1.json" \
  --md "$OUT/score_f1.md" --tool "$TOOL" --set "$SET"

# 5. Speed and memory on this computer.
"$PY" - "$OUT/output" "$SET" <<'EOF'
import json, statistics, sys
out, set_id = sys.argv[1], sys.argv[2]
tasks = [json.loads(x) for x in open(out + "/tasks_log.jsonl", encoding="utf-8") if x.strip()]
meta = json.load(open(out + "/run_meta.json", encoding="utf-8"))
seconds = [t["task_seconds"] for t in tasks]
if set_id == "ref":
    print(f"Time for one document on this computer: {statistics.median(seconds):.2f} s (median of {len(seconds)}).")
else:
    print(f"Time for the {meta['documents']} documents on this computer: {sum(seconds):.1f} s.")
if meta.get("peak_memory_mb"):
    print(f"Peak memory on this computer: {meta['peak_memory_mb']:.0f} MB.")
EOF
echo "Outputs and scores: $OUT"
