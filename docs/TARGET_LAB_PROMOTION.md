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

Current evidence: `target_lab/small_complex_stoich_batch_v1` completed 6/6
jobs. DockQ was strong for `H1233` (`0.850`), moderate for `H1236` (`0.206`),
and weak for `H1232` (`0.023`) despite high confidence. This supports
full-benchmark exact-stoichiometry testing, but it also shows confidence alone
is not a safe promotion signal.

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

Current evidence: the H1258 target-lab window produced a high-confidence
structure but DockQ failed chain mapping against the native reference. Keep it
as a diagnostic until a target-agnostic window rule and reliable chain mapping
exist.

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

## Antibody Fv

Fv-only antibody target-lab runs test whether trimming antibody constant
regions improves antigen-antibody assembly. Promotion requires a
target-agnostic antibody rule that can be generated before prediction from
sequence/metadata alone, and a full benchmark run whose oligo score is judged
with QSglob or another locked server-compatible metric.

Current evidence: `targetlab_protenix_yang_antibody_fv_seed101` completed 8/8
jobs. Diagnostic DockQ succeeded for all 8 jobs, with strong positives on
`H0233__fv` (`0.916`) and `H1233__fv` (`0.891`), moderate signal on
`H1225__fv` (`0.538`) and `H0222__fv` (`0.431`), and weaker mixed signal for
the H0223/H1223/H0225 family. This supports continued O5 strategy work, but it
does not justify direct leaderboard promotion or best-of-target selection.

## Required Post-Run Commands

After target-lab completion:

```bash
python target_lab/small_complex_stoich_batch_v1/summarize_outputs.py
python target_lab/small_complex_stoich_batch_v1/score_dockq.py
python target_lab/domain_fragment_batch_v1/summarize_outputs.py
```

Record the conclusion in `docs/EXPERIMENTS.md` and update
`docs/AUTORESEARCH_QUEUE.md` only with the next full-benchmark action.
