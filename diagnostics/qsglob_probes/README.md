# QSglob Probe Diagnostics

These CSV files are targeted scorer diagnostics, not leaderboard artifacts.
Generate them with `./casp16 qsglob-probe` while long prediction runs are still
active and a full `./casp16 score` would mix partial rows into `leaderboards/*`.

Use these files to inspect OpenStructure mapping messages and choose
target-agnostic scorer or input fixes. Do not use them for per-target strategy
tuning or ranking claims.
