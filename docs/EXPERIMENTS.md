# CASP16 Autoresearch Experiments

This is the append-only working log for CASP16 score-chasing experiments.
Strategy changes should be recorded here before they are interpreted as
leaderboard progress.

## Active Baselines

| Run | Benchmark | Status | Purpose | Rank eligible |
| --- | --- | --- | --- | --- |
| `server_eval_opendde_v1_full_msa_template_bf16_h1220_t1220s1` | `casp16_server_protein_v1` | scored diagnostic | reuse 35 existing OpenDDE local-v1 predictions to expose server coverage gap | no |
| `server_protenix_full_msa_template_seed101` | `casp16_server_protein_v1` | running | full server-target Protenix baseline with real MSA/template settings | yes, once predictions and required scorers exist |
| `server_protenix_yang_terminal_tag_cleanup_seed101` | `casp16_server_protein_v1` | pending, blocked while baseline runs | target-agnostic Yang-style terminal tag cleanup rerun | yes, after baseline frees the GH200 |

## Current Score Truth

- Server domain comparator to beat: `110s`, fixed mean `0.923321`, metric
  `GDT_TS`, 71 targets.
- Server oligo comparator to beat: `456s`, fixed mean `0.582615`, metric
  `QSglob`, 104 targets.
- Current local server diagnostic reuse: domain `0.036428`, oligo `0.000000`.
  The main deficit is coverage and missing QSglob, not just model quality.

## Next Experiment Queue

1. Running `server_protenix_full_msa_template_seed101` on GH200 node
   `c610-032` to generate predictions for the 106 server benchmark Protenix
   jobs.
   - Started by `./casp16 run-next --benchmark casp16_server_protein_v1` inside
     active Vista allocation `797582` at `2026-07-06T01:02:31Z`.
   - Current phase: Protenix MSA/template search with real MSA/templates,
     seed `101`, sample `1`, and `first_output_only`.
   - Startup sanity has passed through Protenix argparse help with `cuda/12.5`,
     Protenix source-first `PYTHONPATH`, and NVIDIA math libs include/library
     paths for `cusparse.h`.
2. Score the domain track immediately after predictions finish; oligo rows will
   stay `metric_unavailable` until an OpenStructure `ost` or equivalent QSglob
   scorer is installed.
3. Run queued `server_protenix_yang_terminal_tag_cleanup_seed101` as the first
   full optimized-input reproduction attempt. It trims only obvious terminal
   His/expression tags and keeps seed `101`, sample `1`, MSA/templates, and
   `first_output_only`.
4. Install OpenStructure `ost` or an equivalent `QSglob` scorer, then rescore
   the oligo track.
5. Start target_lab loops on H1258 and H1232 only as diagnostics for
   stoichiometry/construct tricks; promotion requires a target-agnostic full
   benchmark rerun.
6. Add domain cropping and chain/residue mapping before drawing conclusions
   from hard multi-domain domain targets.

## Strategy Decision Log

### 2026-07-05 Antibody Fv Target-Lab Branch

Decision: generate `yang_antibody_fv_fragment_inputs_v1` as a target-lab
artifact, not as a ranked server run.

Rationale: the broad dynamic-IDR scan found antibody constant-like C-terminal
regions, but trimming all such regions in a ranked strategy would be too broad
without evidence. The narrower Fv branch uses antibody heavy/light prefixes and
variable-domain terminal motifs to trim only obvious constant regions. It
changes 8 antibody-antigen jobs and 16 antibody chains while preserving antigen
chains unchanged.

Use this branch to test whether Fv-only constructs improve antibody-antigen
assembly behavior. Any leaderboard-facing promotion must become a predeclared
target-agnostic antibody-complex rule and run across the full eligible set.

### 2026-07-05 Dynamic Terminal IDR Scan

Decision: do not implement the first dynamic terminal-IDR cleanup heuristic as
a strategy artifact.

Rationale: a sequence-only scan for 60-220 residue terminal disorder-like
segments found 26 candidate protein chains, but the first heuristic was too
broad. It would trim antibody constant-like C-terminal regions in
H0222/H0223/H0225/H1222/H1223/H1225, trim T0240/T1240 C-terminal sequence that
overlaps CASP domain-summary regions, and trim H0272/H1272 poly-alanine/signal
like prefixes. That is too much risk for a ranked server-style rerun.

Useful follow-up:

- split this idea into narrower target-lab branches: antibody/Fv construct
  trimming for the H1222/H1223/H1225 family, and predeclared sequence-only
  terminal-disorder cleanup for long monomers only.
- keep `yang_domain_fragment_inputs_v1` as the safer way to study domain
  decomposition, because it is explicitly marked target-lab and post hoc.
- do not queue a broad dynamic-IDR cleanup run until the rule avoids antibody
  constant regions, avoids known domain-core overlap, and changes only a small
  auditable target set.

## Promotion Rules

- A target_lab improvement is not a leaderboard improvement.
- A manual rescue is not a server-style result unless it becomes an automatic
  target-agnostic rule.
- Confidence can help analyze failures, but it is never a quality score.
- If a trick changes target eligibility, budget, metric identity, or model
  selection policy, create a new benchmark version.
