# Computation Rules

> Current state: done

## Time Parsing

- Input format: `HH:MM:SS`
- Parser converts to total integer seconds
- Invalid or negative values are rejected

## Time Formatting

- Integer seconds to `HH:MM:SS`
- Pace output format: `M:SS /mi`

## T2-Driven Target Run Equation

Given:
- target finish time `target_total_seconds`
- T2 cumulative race time `t2_seconds`

Then:
- `target_run_seconds = target_total_seconds - t2_seconds`

Constraints:
- Must be positive to be valid
- If not positive, show that target finish is no longer achievable from current T2

## Required HM Pace Equation

Given half-marathon distance in miles:
- `HM_MILES = 13.1`

Then:
- `required_pace_seconds_per_mile = target_run_seconds / HM_MILES`

## Ahead/Behind Goal Pace (using run progress)

Given:
- run split cumulative run time at a known run distance
- goal pace (seconds/mile) from target run equation

Then:
- `expected_time_at_distance = goal_pace_seconds_per_mile * distance_miles`
- `delta_seconds = actual_run_time_seconds - expected_time_at_distance`

Interpretation:
- `delta_seconds < 0` => ahead of goal pace
- `delta_seconds > 0` => behind goal pace
- `delta_seconds == 0` => on goal pace

## Split Mapping (Rockford v1 defaults)

- Key markers:
  - `T2` for transition-to-run start
  - Run splits recognized by names containing:
    - `RUN`
    - `MI`
    - `MILE`
  - Priority for final run status:
    - farthest recognized run split distance

## Missing Data Rules

- If no T2 split: show latest split only; no target run math
- If no run split distance/time: show target run and required pace only
- If parsing fails: suppress derived math and show data warning

## Decomposed Tasks

- `tasks/done/015-time-parsing-and-formatting-rules.md`
- `tasks/done/016-t2-driven-target-run-and-required-pace-math.md`
- `tasks/done/017-run-progress-delta-and-split-distance-mapping.md`
- `tasks/done/018-missing-data-and-unachievable-target-handling.md`
