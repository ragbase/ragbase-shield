#!/bin/sh
# Score every pred_<config>_<adapter>.json with the benchmark's own scorer (MIT, downloaded mirror copy, run with
# python -I from outside its folder) in the three matching modes. Usage: sh score_redact.sh [config ...]
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
W="$ROOT/.bench_data/public/redact"
SC="$W/mirror-docs/evaluation_scripts_compute_stratified_f1.py"
for c in ${*:-rules ner-fastino ner-urchade}; do
  for a in plain decomposed; do
    [ -f "$W/pred_${c}_${a}.json" ] || continue
    for m in partial exact fuzzy; do
      "$ROOT/.venv/bin/python" -I "$SC" "$W/pred_${c}_${a}.json" --out "$W/metrics_${c}_${a}_${m}.json" --mode "$m" | grep "^Aggregate" | sed "s/^/$c $a $m /"
    done
  done
done
