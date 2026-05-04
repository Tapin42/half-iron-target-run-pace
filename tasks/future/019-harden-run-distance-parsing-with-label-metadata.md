# Task 019 - Harden Run Distance Parsing with Label Metadata

> Status: future
> Trigger: only if Rockford (or other races) expose run checkpoints in non-v1 formats

## Why

Current run-distance parsing in `src/rtrt_service.py` uses only split name text (`name` or `split`).  
Live Venice data (`IRM-VENICE703-2026`) showed checkpoint formats like `RUN1`/`RUN2` with useful distance details in `label` (for example `Run 2,6 km`), and comma-decimal values that can be misparsed by current regex logic.

This can cause ahead/behind pace status to be missing or inaccurate for intermediate run checkpoints.

## Goals

- Keep existing `T2`/`FINISH` behavior stable.
- Improve distance detection for intermediate run checkpoints.
- Use `label` metadata as a fallback (and optionally `point`/`alias` mappings when needed).
- Correctly handle comma-decimal values (for example `2,6 km`) and dot-decimal values.

## Suggested Implementation Notes

- [ ] Expand normalization to preserve extra split fields needed for parsing (`label`, `point`, `alias`).
- [ ] Update `parse_run_distance()` strategy:
  - [ ] First parse from current split name input.
  - [ ] If missing/invalid, attempt parse from `label`.
  - [ ] Normalize decimal separators (`,` -> `.`) before numeric extraction.
  - [ ] Support meters (`m`) conversion when present (for example `400 m`).
  - [ ] Keep km and mile parsing logic explicit and unit-safe.
- [ ] Add optional point-based fallback mapping (for race-specific formats such as `RUN1`..`RUN9`) only if needed.
- [ ] Ensure `find_best_run_split()` still selects farthest valid run split after T2.

## Test Cases To Add (When Implemented)

- [ ] `RUN1` with label `Run 400 m` -> `0.2485 mi` (approx).
- [ ] `RUN2` with label `Run 2,6 km` -> `1.6156 mi` (approx).
- [ ] `Run 6,1 km` -> `3.7904 mi` (approx).
- [ ] `Run 10 km` -> `6.2137 mi` (approx).
- [ ] `13.1 MI` -> `13.1 mi`.
- [ ] Unknown run name with no numeric metadata -> `None`.
- [ ] Existing Rockford-style names continue to parse as before.

## Acceptance Criteria

- [ ] Ahead/behind pace can be computed from intermediate run checkpoints when distance exists in label metadata.
- [ ] No regression in current T2-anchored target run math.
- [ ] No regression in existing name-based distance parsing paths.
