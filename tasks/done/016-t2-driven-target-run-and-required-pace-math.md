# Task 016 - T2-Driven Target Run and Required Pace Math

> Current state: done
> Spec: `specs/004-computation-rules.md`

- [x] Compute `target_run_seconds = target_total_seconds - t2_seconds`
- [x] Enforce positive `target_run_seconds` as the validity gate
- [x] Compute required pace from `target_run_seconds / 13.1`
- [x] Output required run values in both `HH:MM:SS` and `M:SS /mi` where relevant
- [x] Add/update tests for valid, boundary, and unachievable-target scenarios
