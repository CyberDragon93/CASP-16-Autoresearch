# CASP16 Winner Reproduction Board

This is the short control board for the score-chasing loop. Keep the long
evidence and history in `docs/CASP16_WINNER_RECIPES.md`,
`docs/AUTORESEARCH.md`, and `docs/AUTORESEARCH_QUEUE.md`; use this file when
choosing the next concrete branch.

## Current Score Target

Official server leaders to beat on the local server-style comparator:

| Track | Official metric | Fixed targets | Server leader | Mean to beat |
| --- | --- | ---: | --- | ---: |
| protein domain | GDT_TS | 71 | `110s` | `0.923321` |
| protein oligo | QSglob | 104 | `456s` | `0.582615` |

Current best complete local server-v2 attack baseline:

| Run | Budget | Domain | Oligo | Full fixed-set mean |
| --- | --- | ---: | ---: | ---: |
| `server_v2_attack_scoreable_input_repair_overlay_msa_reuse_protenix5_seed101_105` | 5 candidates, confidence selector | `0.107690` | `0.118933` | `0.114371554` |

This is not close to the winners yet. The immediate goal is to raise valid
scoreable-target signal and coverage without using references or official
per-target scores during prediction.

## Active Gate

Checked `2026-07-07 14:09 CDT`: P25 is still incomplete.

| Gate | Status |
| --- | --- |
| run family | `casp16_server_attack_protenix25_scoreable_input_repair` |
| benchmark | `casp16_server_protein_v2_aliasfix` |
| observed candidates | `1106` |
| shard-level missing candidates | `944` |
| full 25-candidate slots still missing | `874` |
| complete full-budget tasks | `1 / 79` |
| Slurm | 19 P25 jobs running, 5 P25 jobs pending behind `QOSMaxJobsPerUserLimit` |
| action | wait for declared candidates, then run the P25 closeout wrapper |

Do not score the P25 row or launch O5b/P27b/D6a from partial outputs.

## Recipe Reproduction Board

| Winner clue | Local reproduction | Current evidence | Next action | Stop or skip condition |
| --- | --- | --- | --- | --- |
| Top domain servers had broad coverage and high automatic accuracy | Yang-style input repair: sequence recovery, phase aliases, low-complexity cleanup, token-safe fallback | P17 repaired the 5 scoreable missing-prediction rows and is the best complete local server-v2 row | Keep P17 as the seed101-105 overlay for P25 | Stop adding input-cleanup variants until P25 shows a specific failure class |
| Winner-scale systems use multiple internal candidates, but ranking is fragile | P25: 25 fixed seeds on the repaired 79-job scoreable subset with `protenix_confidence_v1` | Submitted as Slurm jobs `812935..812958`; MSA preflight was complete; still running | Finish P25, merge, score, regenerate leaderboard, then inspect aggregate deltas | Never score a partial 25-candidate row; if flat and valid, do not just add more seeds |
| MULTICOM/QA-style systems rely on diverse model/MSA pools plus QA | P27b repaired-input default-params model/config variant; broader MSA/model diversity design gate | P27b is prepared and MSA-clean, but deferred behind P25 | If complete P25 is flat with valid predictions/metrics, launch P27b before another seed grid | Do not turn off MSA or use toy settings; do not choose variants per target from scores |
| Complex winners/top methods still struggle on antibodies and high-order stoichiometry; specialized handling can help | O5b repaired-input antibody/Fv branch | Target-lab Fv diagnostics were positive, and O5b preflight is clean | Launch only if P25 shows antibody/Fv oligos are the dominant recoverable weakness | Do not use target-lab DockQ positives as leaderboard evidence |
| Domain decomposition and construct boundaries matter | D6a domain sequence recovery after warmup; domain-fragment target-lab evidence | D6a MSA reuse is complete after warmup | Launch D6a only if P25 domain zeros cluster around input-kind/alias/domain classes | Do not hand-pick CASP domain crops from target scores |
| Local comparison is capped by missing references and QSglob mapping | Versioned refmap work: v4 now has 81/175 refs; v5 queue is lane-based | Lane E relaxed RCSB probe added no promotable rows; H1265 input aliases are repaired but reference-blocked | Continue only strict v5 reference lanes while GPU jobs run | Do not patch v2/v4 in place or promote sequence hits without native/reference proof |

## Post-P25 Decision

Use only the complete merged P25 score and the read-only helper:

```bash
scripts/finish_p25_scoreable_input_repair.sh --dry-run \
  --output-tsv /tmp/casp16_p25_readiness_live.tsv
scripts/finish_p25_scoreable_input_repair.sh
./casp16 post-p25-readout --benchmark casp16_server_protein_v2_aliasfix
```

Decision order:

1. P25 improves broadly over P17: analyze target deltas and selector behavior
   before launching anything else.
2. P25 is flat but valid: launch P27b model/config diversity.
3. P25 domain failures cluster on input-kind/alias/domain classes: launch D6a.
4. P25 oligo failures cluster on antibody/Fv rows: launch O5b.
5. P25 is mostly reference-capped: continue versioned refmap work, not GPU.

## File Map

| File | Role |
| --- | --- |
| `docs/CASP16_WINNER_RECIPES.md` | Long recipe rationale and source-to-experiment mapping |
| `docs/AUTORESEARCH.md` | Append-only current truth and experiment history |
| `docs/AUTORESEARCH_QUEUE.md` | Executable queue and branch gates |
| `docs/SERVER_SCORE_TARGETS.md` | Exact score targets, active closeout commands, and comparator rules |
| `docs/MSA_CACHE_PLAN.md` | MSA reuse policy and launch hygiene |
| `docs/REFERENCE_RECOVERY_V5_PLAN.md` | Versioned reference-recovery plan |
| `AGENTS.md` | Rules for agents and humans before modifying strategies or runs |
