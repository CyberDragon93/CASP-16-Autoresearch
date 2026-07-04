# Strategy Record Template

Use this template for each new leaderboard-facing run.

## Identity

- Run ID:
- Strategy name:
- Parent run:
- Author/agent:
- Date:

## Hypothesis

State the expected improvement in one or two sentences.

## Changes

- Changed knobs:
- Changed code/scripts:
- Unchanged fixed budget:
  - backend: `protenix`
  - seed: `101`
  - sample count: `1`
  - selected model policy: `first_output_only`

## Commands Used

```bash
./casp16 run-spec --run-id <run_id> --benchmark casp16_protein_v1
./casp16 run-next --benchmark casp16_protein_v1
./casp16 score --benchmark casp16_protein_v1
./casp16 leaderboard --benchmark casp16_protein_v1
```

## Result Summary

- Rank status:
- Mean score:
- Eligible targets:
- OK targets:
- Missing targets:
- Failed targets:
- Metric unavailable targets:
- Artifact path:

## Failure Notes

Describe crashes, missing outputs, metric failures, or targets that need
coverage follow-up.

## No-Oracle Checklist

- [ ] Did not inspect native/reference structures before prediction.
- [ ] Did not use official score tables for target-specific tuning.
- [ ] Did not use previous target scores for target-specific parameter choices.
- [ ] Did not replace structure metrics with confidence diagnostics.
- [ ] Regenerated results only through `./casp16 score` and
      `./casp16 leaderboard`.

## Next Action

State the next planned strategy, cleanup, or investigation.

