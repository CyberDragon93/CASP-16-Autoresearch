# Target-Lab Promotion Gates

Target-lab jobs are fast learning probes for winner-style recipes. They are not
ranked CASP16 server results, and they must not be registered as leaderboard
runs. Promote only target-agnostic rules that can be rerun through `./casp16`
on the fixed benchmark.

## General Rules

- Do not use native structures, official scores, or previous target scores to
  choose a target-specific window, crop, seed, or model.
- Confidence is a triage signal only. A high pLDDT/pTM/ipTM target-lab model is
  not proof of quality.
- A target-lab result can justify a full benchmark run only when the rule can be
  generated from allowed inputs: sequence, target metadata, public method notes,
  run logs, and benchmark manifests.
- A full benchmark promotion must be a new strategy artifact under
  `strategies/<strategy>/...` plus a normal `runs/<run_id>/run_spec.json`.

## Exact Stoichiometry

Promote exact-stoichiometry changes when:

- the target-lab batch finishes without systematic Protenix failures,
- at least the under-budget exact-stoich cases produce structures and
  confidence files,
- DockQ/QSglob diagnostics do not show obvious assembly collapse, and
- the full benchmark strategy preserves the same fixed seed/sample budget.

Do not promote an exact full assembly if it exceeds the Protenix token limit.
Use the existing token-safe derivative or a separately declared window/fallback
policy.

## H1258-Style Windows

The H1258 interaction window is a public-clue reproduction, not a ranked
strategy. It can become a full benchmark idea only if converted into a
target-agnostic rule, for example:

- crop long partner chains by public domain annotations available before
  prediction,
- crop long low-complexity/disordered terminal regions by sequence-only rules,
  or
- generate a predeclared window budget tier with fixed candidate accounting.

Do not promote a hard-coded residue window for a single CASP target into a
server leaderboard run.

## Domain Fragments

Domain-fragment target_lab runs test the upper-bound value of decomposition.
Promotion requires a rule that does not depend on CASP native-domain answers for
the ranked benchmark:

- sequence-only segmentation,
- public domain annotation segmentation,
- model-independent length/token segmentation, or
- a new benchmark version explicitly labeled as domain-fragment diagnostic.

CASP domain-summary hand crops stay target_lab-only unless a new benchmark
version is created.

## Required Post-Run Commands

After target-lab completion:

```bash
python target_lab/small_complex_stoich_batch_v1/summarize_outputs.py
python target_lab/small_complex_stoich_batch_v1/score_dockq.py
python target_lab/domain_fragment_batch_v1/summarize_outputs.py
```

Record the conclusion in `docs/EXPERIMENTS.md` and update
`docs/AUTORESEARCH_QUEUE.md` only with the next full-benchmark action.
