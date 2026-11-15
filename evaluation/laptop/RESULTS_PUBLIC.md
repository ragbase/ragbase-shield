# Benchmark: RAGbase Shield 0.4.1

How we measure Shield, and the results. En français : https://shield.ragbase.ai/resultats/

## What we measure

Masking everything is easy, but then the AI cannot do the work. A good pseudonymisation engine masks the personal
data and leaves the rest of the document intact. So we measure both at the same time.

| Measure | What it says | Better |
|---|---|---|
| Overall score (F1) | Computed word by word. It drops when a tool leaves personal data readable (recall, R) and when it masks text that it must keep (precision, P). | higher |
| Legal terms changed | The share of court names, articles, codes and laws that the tool changed by mistake. | lower |
| Speed and memory | Time and peak memory to process one 10-page document. | lower |

## Tools

| Tool | Version | Modes |
|---|---|---|
| RAGbase Shield | 0.4.1 | Fast (rules only, the default) and Precise (rules and a GLiNER model on the CPU) |
| Hexagone AI Desktop | 0.3.9 | Fast and Precis, default settings |
| Microsoft Presidio | 2.2.364 | default recognizers, spaCy `fr_core_news_md` |

## Benchmarks

Four benchmarks in French, all public. Two come from other teams. Two are written by RAGbase with invented people
and companies.

| Benchmark | Content | Size |
|---|---|---|
| [FR-PII-Bench](https://huggingface.co/datasets/JaqueBill/fr-pii-bench) | French texts with personal data | 300 texts, 2,105 personal data items |
| MAPA | Decisions of the Cour de cassation | 19 decisions, 1,615 personal data items, 1,344 legal terms |
| [REF](../datasets/ref) (RAGbase) | An employment-law brief in five versions | 5 documents, 1,015 personal data items, 365 legal terms |
| [Max](../datasets/max) (RAGbase) | Law-firm matters in Word, PDF, Excel and text | 33 documents, 1,003 personal data items, 144 legal terms |

Every tool gets the same files, on the same machine: 6 cores, 16 GB of memory, no graphics card. The same program
scores every output.

REF and Max are in [`evaluation/datasets`](../datasets) with their answer keys. Run them on your own computer.

## Results

The best value of each row is in bold.

### Overall score (F1), higher is better

Precision (P) and recall (R) are next to each score.

| Benchmark | Shield Fast | Shield Precise | Hexagone Fast | Hexagone Precis | Presidio |
|---|---|---|---|---|---|
| FR-PII-Bench | **96.9** (P 95.0, R 98.9) | 96.2 (P 93.6, R 99.1) | 80.7 (P 68.4, R 98.4) | 80.7 (P 67.7, R 99.9) | 66.5 (P 69.2, R 64.1) |
| MAPA | 80.4 (P 81.8, R 79.1) | **82.2** (P 77.6, R 87.3) | 43.8 (P 28.5, R 95.3) | 37.9 (P 23.8, R 93.9) | 63.5 (P 51.0, R 84.1) |
| REF | **97.1** (P 97.9, R 96.2) | **97.1** (P 97.9, R 96.2) | 66.7 (P 50.6, R 97.6) | 61.1 (P 44.0, R 99.9) | 79.2 (P 82.5, R 76.1) |
| Max | **95.3** (P 95.9, R 94.7) | 91.8 (P 88.5, R 95.3) | 54.0 (P 38.1, R 92.4) | 48.9 (P 32.7, R 96.2) | 47.4 (P 38.0, R 63.0) |

### Legal terms changed, lower is better

| Benchmark | Shield Fast | Shield Precise | Hexagone Fast | Hexagone Precis | Presidio |
|---|---|---|---|---|---|
| MAPA | **0.0 %** | **0.0 %** | 43.1 % | 47.6 % | 18.0 % |
| REF | **4.1 %** | **4.1 %** | 17.8 % | 47.1 % | 15.3 % |
| Max | **2.1 %** | 4.2 % | 47.2 % | 58.3 % | 55.6 % |

### Speed and memory, lower is better

| | Shield Fast | Shield Precise | Hexagone Fast | Hexagone Precis | Presidio |
|---|---|---|---|---|---|
| Time for one document | **0.61 s** | 17.7 s | 26.93 s | 9 min | 1.59 s |
| Peak memory | **78 to 79 MB** | 3.7 to 3.8 GB | 1.6 to 1.7 GB | 3.8 to 5.4 GB | 0.57 GB |

## Run it yourself

The scripts are in this folder and in [`evaluation/public`](../public). For REF and Max, one command installs the
tool, runs it and prints the scores: `bash evaluation/datasets/reproduce.sh ref`.

| Script | What it does |
|---|---|
| `../public/*/download.py` | Downloads a public benchmark |
| `run_shield_files.py` | Runs Shield on a folder of files, in Fast or Precise mode |
| `run_presidio.py` | Runs Presidio on the same files |
| `extract_text.py` | Reads the text of an input file and of a tool's output file |
| `score_text.py` | Scores an output against the benchmark answers |
| `score_f1.py` | Computes the overall score (F1) with precision and recall |
| `../datasets/reproduce.sh` | Runs Shield or Presidio on REF or Max and prints the scores, in one command |
