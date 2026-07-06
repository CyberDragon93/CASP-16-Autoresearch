# CASP16 Winner Recipes

This file records public CASP16 method clues that are useful for future local
strategy iteration. It is not a license to use official references or scores as
per-target oracles.

## Sources

- CASP16 home and category description:
  https://predictioncenter.org/casp16/
- CASP16 official score tables:
  https://predictioncenter.org/download_area/CASP16/results/tables/
- CASP16 domain z-score ranking:
  https://predictioncenter.org/casp16/zscores_final.cgi
- Yang Lab CASP16 optimized-input paper:
  https://yanglab.qd.sdu.edu.cn/papers/Wang_Proteins_2026.pdf
- CASP16 single-protein assessment:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC12157625/
- CASP16 protein-complex assessment preprint:
  https://www.biorxiv.org/content/10.1101/2025.05.29.656875v1.full.pdf
- AlphaFold3 CASP16 preprint:
  https://www.biorxiv.org/content/10.1101/2025.04.10.648174v1.full-text

## Protein Domains

Public reports and the CASP16 domain z-score page indicate that Yang-lab
systems were at or near the top of CASP16 protein-domain performance. The
public recipe is not a single new architecture; it is careful input and target
handling around strong predictors.

Useful strategy hypotheses:

- trim or mask intrinsically disordered regions before prediction when the
  structured core is the scoring target
- decompose multi-domain targets when domain boundaries are clear
- run multiple strong engines where available, such as AF2-style, AF3-style,
  and trRosettaX-style systems
- optimize MSA and template inputs instead of accepting default shallow inputs
- improve model ranking; CASP assessments repeatedly flag ranking/selection as
  a weakness even when at least one generated model is good

For local work, these ideas should become strategy scripts that transform
inputs or select allowed outputs under a fixed budget. They must not change the
benchmark target set or inspect references.

### Recipe Cards

| ID | Recipe | CASP16 clue | Local implementation | Promotion gate |
| --- | --- | --- | --- | --- |
| D1 | Construct trimming | Yang-lab reports removed intrinsically disordered regions and CASP16 monomer assessment highlights fragment/construct design | create target-agnostic sequence-window variants from disorder/low-complexity predictors; never choose windows from reference scores | improves full `protein_domain` mean, not only a handpicked target |
| D1a | Terminal tag cleanup | Yang-style optimized inputs are a low-risk place to remove non-native expression artifacts before harder construct work | `./casp16 strategy-inputs --strategy yang_terminal_tag_cleanup_v1` removes obvious terminal His/expression tags without changing benchmark files | improves or does not regress full server-domain mean after the full baseline |
| D1b | Epitope/TEV tag cleanup | some server inputs visibly include longer N-terminal epitope/His/TEV expression artifacts | `./casp16 strategy-inputs --strategy yang_epitope_tag_cleanup_v1` extends D1a to FLAG-like and His-TEV prefixes while staying sequence-only | queued behind lower-risk construct ablations; judge only by full-set mean |
| D1c | Terminal low-complexity cleanup | Yang-style construct refinement often removes disordered terminal noise; CASP monomer assessment highlights construct design | `./casp16 strategy-inputs --strategy yang_low_complexity_terminal_cleanup_v1` trims only 40-aa terminal low-complexity windows after tag cleanup | queue only after conservative tag cleanup helps or baseline failures justify the extra risk |
| D1d | Hydrophobic leader cleanup | construct refinement can remove signal-like N-terminal leaders that are not part of the scored folded core | `./casp16 strategy-inputs --strategy yang_hydrophobic_leader_cleanup_v1` trims a small set of sequence-only hydrophobic-leader candidates after D1c | risky branch; queue only after baseline or tag-cleanup evidence justifies it |
| D1e | Conservative construct stack | non-overlapping low-risk construct cleanups may compose better than either ablation alone | `./casp16 strategy-inputs --strategy yang_terminal_tag_antibody_fv_cleanup_v1` stacks terminal tag cleanup with antibody Fv cleanup on the full server set | deferred after antibody-Fv cleanup was negative on domains and unmeasurable on oligos |
| D2 | Domain decomposition | top monomer pipelines refined constructs and handled domains separately | `./casp16 strategy-inputs --strategy yang_domain_fragment_inputs_v1` creates post hoc CASP-domain fragment inputs for target-lab learning | not server-ranked; promotion needs a new benchmark version or predeclared segmentation rule |
| D2a | Domain fragment batch | domain decomposition needs fast feedback before full benchmark promotion | `target_lab/domain_fragment_batch_v1/` runs 12 selected fragments from long and multidomain protein targets | target_lab only; use results to design target-agnostic segmentation |
| D3 | MSA/template depth | Yang/trRosetta workflows emphasize optimized MSA/template inputs | full MSA/template Protenix/OpenDDE server run; record MSA source, template mode, cache paths | higher full-set coverage and no regression on positive controls |
| D4 | AF3-style model selection | assessment says AF3 adoption improved confidence/model selection | `protenix_confidence_v1` is implemented for the separate `server_attack` tier; `dev_fixed` remains first-output-only | attack runs must use the locked seed/sample budget and never compare directly against `dev_fixed` rows |
| D5 | Large-target split/fallback | top methods used target handling and construct/domain decomposition; baseline Protenix lost 8 jobs to `n_token > 2560` before prediction | `./casp16 strategy-inputs --strategy yang_large_target_split_or_fallback_v1` predeclares chain/copy fallback for all eight hard failures after the conservative `T1295` probe | treat as coverage recovery; assembly quality may regress when chains are dropped |
| D6 | Sequence recovery | server-style coverage fails if target sequence archives are parsed or aliased incorrectly | `./casp16 strategy-inputs --strategy yang_sequence_recovery_v1 --input-json strategies/yang_terminal_tag_cleanup_v1/.../inputs.json` recovers protein-like records as `proteinChain` | queue after active jobs; do not use references or scores to choose recovered targets |
| D7 | Coverage-first stack | realistic attack compute should not be spent on missing-sequence or token-limit hard zeros | `yang_sequence_recovery_large_target_fallback_v1` stacks sequence recovery with the large-target fallback on terminal-tag-cleaned inputs | queue after the component runs or when the queue needs a single combined coverage candidate |

## Protein Oligos

Protein-complex performance is driven by more than per-chain fold quality.
Assembly stoichiometry, symmetry, chain placement, and interface correctness
matter. Public CASP16 complex reports highlighted strong multimer groups and
continued room for improvement in complex modeling.

Useful strategy hypotheses:

- preserve exact stoichiometry from CASP target metadata
- build assembly-aware inputs rather than flattening all chains naively
- use symmetry-aware chain assignment in scoring and diagnostics
- keep interface metrics such as DockQ, but optimize for assembly-level
  `QSglob` once the scorer is available
- separate "automatic server-like" runs from manual rescue runs

For the server benchmark, a method that produces good monomer structures but
wrong assemblies should score poorly on the oligo track.

### Recipe Cards

| ID | Recipe | CASP16 clue | Local implementation | Promotion gate |
| --- | --- | --- | --- | --- |
| O1 | Exact stoichiometry | Phase 0 showed stoichiometry is still hard, especially high-order assemblies | preserve `Oligo.State`, validate chain counts, fail fast when input expansion is ambiguous | no silent chain/entity mismatch in `input_manifest.tsv` |
| O1a | Server stoichiometry recovery | local server-target rows can lose explicit target-list stoichiometry and collapse assemblies to one copy per entity | `yang_oligo_stoichiometry_recovery_v1` restores official parsed `Oligo.State` for protein-only oligo jobs | queue only a token-safe or windowed derivative; exact recovered full assemblies can exceed Protenix limits |
| O1b | Token-safe stoichiometry | exact stoichiometry helps only if the assembly is still runnable under the fixed Protenix budget | `yang_oligo_stoichiometry_token_safe_v1` starts from stacked coverage recovery and restores only under-budget copy counts | queue as a full benchmark candidate after current coverage runs |
| O1c | Protein-oligo sequence recovery | a realistic server input must not turn protein complex targets into RNA/DNA jobs or drop alias targets | `yang_protein_oligo_sequence_recovery_v1` recovers protein-like official sequence records for protein-oligo rows such as `H0220/H1220/H2220` | promote only as a full-benchmark input repair; do not hand-select recovered targets from score feedback |
| O1d | Sequence + stoichiometry stack | recovered protein oligo sequences should carry the official assembly copy counts when that remains under budget | `yang_protein_oligo_sequence_stoich_token_safe_v1` composes O1c with token-safe official `Oligo.State` recovery on v2 alias-fixed inputs | queue only after active v2 evidence, or compose with the no-over-token fallback before attack-budget runs |
| O1e | Oligo-recovery nofail stack | winner-scale compute should be spent on runnable jobs with correct input modality, not old over-token or nucleic-acid misparsed inputs | `yang_oligo_sequence_stoich_low_complexity_large_fallback_v1` composes O1c/O1d with low-complexity cleanup and large-target fallback; 165 jobs, max 2535 tokens, 0 over-token | current preferred v2 nofail input for `dev_fixed` and `protenix5` attack runs |
| O2 | Construct refinement | complex assessment highlights partial constructs over full sequences | generate target-agnostic construct variants from sequence/domain annotations for large complexes | improves fixed-set QSglob only after scorer mapping is validated; DockQ-only wins stay diagnostic |
| O2a | H1258 public interaction window | CASP16 complex assessment notes top Yang H1258 models used the LRRK2 interacting region rather than full-length LRRK2 | `target_lab/h1258_interaction_window_v1/` builds LRRK2 861-1014 plus 14-3-3 A1B2 | target_lab only; promotion requires a target-agnostic window rule |
| O2b | Small complex learning batch | exact stoichiometry and construct windows need faster feedback than full-benchmark runs | `target_lab/small_complex_stoich_batch_v1/` batches 5 exact-stoich jobs plus H1258 window | target_lab only; use for promotion decisions, not direct ranking |
| O3 | Customized MSA/template | top complex groups beat default AFM/AF3 via customized MSAs, templates, and sampling | full MSA/template baseline first, then compare MSA-cache and template modes | full server target coverage increases before target_lab tuning |
| O4 | Massive sampling + ranking | MULTICOM/Kihara-style gains came from sampling, but ranking stayed weak | `attack_budgets/casp16_server_attack_protenix5.json` defines the starter 5-candidate attack tier; `attack_budgets/casp16_server_attack_protenix25*.json` declares planned 25-seed v2 tiers; every run must expose `budget_tier` and `candidate_count` | launch only after the target question is worth multi-seed compute and budget accounting is recorded |
| O5 | Antibody docking branch | kozakovvajda did especially well on antibody-antigen targets without AFM/AF3 as the core engine | `yang_antibody_fv_cleanup_v1` completed a full-set run; `targetlab_protenix_yang_antibody_fv_seed101` completed as a target_lab Fv-only diagnostic with strongest confidence signal on H0233/H1233 | do not promote until QSglob assembly mapping can evaluate the antibody oligo predictions |
| O6 | First-model ranking | PEZYFoldings was noted for stronger first-model selection | evaluate confidence/consensus/geometry features after full predictions exist | selection rule fixed before scoring a new full run |
| O7 | Oversize complex fallback | complex targets can exceed AF3-like token limits, and the baseline lost H0217/H0258/H0272/H1217/H1258/H1272 before any model was produced | `yang_large_target_split_or_fallback_v1` keeps under-budget chain/copy prefixes and records dropped chains | score as coverage recovery until QSglob and assembly mapping are trustworthy |

## AF3-Style Systems

AF3-style predictors are strong CASP16 baselines, especially when inputs and
large-target handling are carefully managed. Public AF3 CASP16 reports also
describe manual intervention for some difficult or large targets, which should
be tracked separately from server-like automatic runs.

Useful strategy hypotheses:

- compare OpenDDE/Protenix-style runs against an AF3-style reference strategy
  where licensing and local execution allow it
- record whether a run is automatic or manually adjusted
- collect confidence as diagnostics only; do not rank by confidence

## What To Avoid

- claiming a server-track win from `casp16_protein_v1`
- optimizing target-specific settings after seeing official scores
- rescuing a few targets while ignoring full-set mean score
- treating DockQ as interchangeable with `QSglob`
- treating TM-score as interchangeable with official domain `GDT_TS`

## Active Reproduction Order

1. Full server-target MSA/template baseline with Protenix: completed with
   domain mean `0.063962`, 98/106 generated CIFs, and 8 `n_token > 2560`
   failures. This is the first real baseline, not a competitive score.
2. `yang_terminal_tag_cleanup_v1`: completed and is the current best local
   server-domain `dev_fixed` run, with mean `0.066908`.
3. `yang_oversize_domain_monomer_fallback_v1`: completed and rescued `T1295`
   inference but not score, because local reference mapping is missing.
4. `yang_antibody_fv_cleanup_v1`: completed as a negative domain result
   (`0.060677`); antibody oligo predictions cannot be judged until QSglob
   assembly mapping is validated.
5. `yang_terminal_tag_antibody_fv_cleanup_v1` and
   `yang_epitope_tag_cleanup_v1`: deferred. Do not launch until QSglob mapping,
   large-target split policy, or a new positive signal makes the full run worth
   the compute.
6. `yang_low_complexity_terminal_cleanup_v1` and
   `yang_hydrophobic_leader_cleanup_v1`: generated as risk-increasing
   construct-cleanup artifacts; promote only after baseline or conservative
   cleanup evidence.
7. `yang_large_target_split_or_fallback_v1`: generated and queued as
   `server_protenix_yang_large_target_split_or_fallback_seed101`; run after
   the active attack job if coverage recovery remains higher leverage than
   another construct cleanup.
8. `yang_sequence_recovery_v1`: generated on top of terminal-tag cleanup to
   recover missing/misparsed protein-domain inputs such as `T1212`,
   `T1239V1/V2`, and `T2280`.
9. `yang_sequence_recovery_large_target_fallback_v1`: generated and queued as
   `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` on
   top of terminal-tag cleanup to combine sequence recovery with token-budget
   fallback. It changes 40 unique targets and keeps the largest optimized job
   at 2535 tokens.
10. `yang_oligo_stoichiometry_recovery_v1`: generated as an exact
   stoichiometry artifact on top of terminal-tag cleanup. It changes 9 existing
   oligo jobs; 5 remain under the Protenix limit and 4 expose the need for
   construct/domain-window strategies.
11. `yang_oligo_stoichiometry_token_safe_v1`: generated and queued as
    `server_protenix_yang_oligo_stoichiometry_token_safe_seed101` on top of
    stacked coverage recovery. It changes the 5 under-budget
    exact-stoichiometry oligo jobs while keeping the largest optimized job at
    2535 tokens.
12. `yang_protein_oligo_sequence_recovery_v1`: generated on
    `casp16_server_protein_v2_aliasfix` to recover protein-oligo inputs that
    were locally missing or parsed as nucleic-acid jobs despite official
    protein-like sequence records. It changes `H0220`, `H1213`, `H1220`,
    `H2213`, and `H2220`.
13. `yang_protein_oligo_sequence_stoich_token_safe_v1`: generated on
    `casp16_server_protein_v2_aliasfix` to compose oligo sequence recovery with
    token-safe stoichiometry recovery. It changes 15 unique targets, including
    `H1220/H2220` sequence recovery plus `A1B4` stoichiometry, but it is not a
    no-over-token full-stack artifact because unrelated v2 jobs such as
    `H0272` still exceed Protenix's token limit.
14. `yang_oligo_sequence_stoich_low_complexity_large_fallback_v1`: generated
    and registered as both
    `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`
    and the MSA-reused
    `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105`.
    It keeps protein-oligo sequence recovery, token-safe stoichiometry,
    low-complexity cleanup, and large-target fallback together; 165 jobs, max
    2535 tokens, 0 jobs above the Protenix limit.
    The hydrophobic-leader derivative
    `server_v2_protenix_yang_oligo_sequence_stoich_hydrophobic_leader_nofail_msa_reuse_seed101`
    is queued as a narrow D1d ablation on top of this stack: 8 changed
    T0240/T1210/T1240 alias sequences, 0 over-token jobs, and 260/268 MSA paths
    reused.
    The full-input dev row was later cancelled after 39/165 CIFs when it spent
    extended time on local `no_reference_pdb` target `T1295`; keep those
    partial artifacts only as MSA/cache evidence until references are recovered.
15. `scoreable_target_subset_v1`: generated on
    `casp16_server_protein_v2_aliasfix` to spend attack compute only on jobs
    that can currently affect local score. It keeps 74/165 jobs, skips 91
    no-reference jobs, preserves the fixed 175-target scoring set, and reuses
    141/141 exact-sequence MSA paths in the running
    `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105`.
16. `casp16_server_attack_protenix25_scoreable_nofail`: planned but not queued.
    It is the winner-scale 25-seed successor to the running scoreable
    `protenix5` attack. Launch only if the 5-seed scoreable row gives a reason
    to spend the GPU-hours; keep the older 165-job `protenix25_nofail` plan as
    a full-input ablation until reference recovery.
17. `target_lab/h1258_interaction_window_v1`: generated a target-lab-only
    public interaction-window input with LRRK2 residues 861-1014 and 14-3-3
    A1B2 stoichiometry. Total length is 648 tokens.
18. `target_lab/small_complex_stoich_batch_v1`: generated a six-job compact
    complex batch with exact-stoichiometry targets and the H1258 window. Max
    job length is 1929 tokens.
19. QSglob scorer installation/integration: without this, oligo server runs
    remain diagnostic no matter how good the structures look.
20. `server_attack` budget: `server_attack_protenix_terminal_tag_seed101_105`
    is the first queued 5-candidate terminal-tag attack run; use only for a
    separate multi-candidate comparison. It is currently incomplete: latest
    output has complete `seed_101`/`seed_102` and partial `seed_103`, so it
    must not be scored as a complete 5-candidate row.
21. `server_attack_protenix_coverage_stoich_seed101_105`: generated as the
    second queued 5-candidate attack run, using stacked sequence recovery,
    token-budget fallback, and token-safe stoichiometry inputs. It has been
    superseded by `server_attack_protenix_coverage_stoich_msa_reuse_seed101_105`
    to avoid repeated MSA search, but that successor still misses 16/196
    exact-sequence MSA sources and is lower priority than the v2 scoreable
    nofail path.
22. `server_v2_protenix_yang_coverage_stoich_low_complexity_seed101`: queued
    as a v2 `dev_fixed` construct-cleanup ablation. It starts from the
    alias-fixed coverage/stoich input, changes 27 sequences across 21 targets
    with terminal tag/low-complexity cleanup, and should stay an ablation behind
    the scoreable nofail attack line.
23. `server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101`:
    queued as the v2 coverage-recovery ablation after low-complexity cleanup.
    It applies the target-agnostic large-target fallback to the 11 v2 jobs
    still above 2560 tokens and leaves 0 over-token jobs.
24. `casp16_server_attack_protenix25`: planned but not queued. It targets the
    alias-fixed v2 server benchmark with seeds `101..125`, one sample per seed,
    and `protenix_confidence_v1`; the shard run ids and seed ranges are locked
    in `attack_budgets/casp16_server_attack_protenix25_shards.tsv`. Keep as a
    broader full-input budget; the scoreable 25-seed budget is the current
    preferred scale-up while references are incomplete.
25. `casp16_server_attack_protenix25_nofail`: planned but not queued. It uses
    the same 25-seed budget on the MSA-reused v2 no-over-token fallback input,
    with shard rows locked in
    `attack_budgets/casp16_server_attack_protenix25_nofail_shards.tsv`.
    The budget now points at
    `inputs_msa_reuse_from_dev_seed101.json`, so any launch spends the 25-seed
    tier on the current protein-oligo sequence recovery nofail stack without
    repeating MSA search in every shard.
26. `server_v2_attack_nofail_protenix5_seed101_105`: queued but not submitted
    as the first five-candidate attack on the no-over-token v2 stack. It uses
    seeds `101..105` and `protenix_confidence_v1`, and waits behind the three
    v2 `dev_fixed` rows. It is now superseded by
    `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105`
    unless an ablation requires the older input.
27. `yang_domain_fragment_inputs_v1`: generated as a target-lab artifact using
    CASP domain-summary metadata; useful for learning whether domain
    decomposition helps, but not a server-ranked strategy as-is.
28. `target_lab/domain_fragment_batch_v1`: generated and submitted as Slurm job
    `810862`. It runs 12 domain-fragment jobs from T1210, T1218, T1269, T1257,
    T1240, and T1270 to test the domain-decomposition recipe quickly.
29. `yang_antibody_fv_fragment_inputs_v1`: generated as a target-lab artifact
    for antibody-antigen complexes, trimming antibody constant regions while
    preserving antigen chains. It is now queued through
    `targetlab_protenix_yang_antibody_fv_seed101` as Slurm job `811918`,
    completed with 8/8 CIFs. H0233/H1233 are the clearest confidence-positive
    cases; this is useful for O5 learning, not a server-ranked strategy as-is.
30. Domain crop/chain mapping: needed before domain scores can be trusted on
    multi-domain or multi-chain targets.
31. H1258/H1232 target_lab loop: use these as fast learning targets for
    stoichiometry, construct refinement, and antibody-complex behavior, then
    promote only target-agnostic changes.
32. Model-selection research: collect confidence/consensus after predictions,
    but keep ranked `first_output_only` unless a new benchmark version is
    created.
