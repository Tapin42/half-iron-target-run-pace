# Athlete Management Consistency Design

## Context

The current flow allows the same athlete to be configured multiple times. This creates confusion in the athlete list and makes target-time changes indirect. The design goal is a simple, consistent management model that handles:

- duplicate prevention when adding athletes
- target time updates for existing athletes
- safe athlete deletion

## Goals

- Keep `Configure Athlete` as the entry point for adding athletes.
- Keep edits and deletes fast in the main `Athlete List`.
- Enforce duplicate prevention server-side.
- Avoid hidden behavior (no silent overwrite on duplicate add).

## Non-Goals

- Reworking athlete detail page ownership model.
- Adding modal dialogs or multi-page management flows.
- Introducing polling or background refresh changes.

## Agreed UX Model

### Configure Athlete

- User searches/selects an athlete and enters target finish time.
- On save, the server checks whether this athlete is already configured.
- If duplicate: stay on config page and show a clear warning with a link back to the athlete list to edit target time there.

### Athlete List as Management Surface

Each row supports inline actions:

- `Edit target` -> toggles inline `HH:MM:SS` input with `Save` and `Cancel`
- `Delete` -> toggles inline confirmation controls:
  - `Confirm delete`
  - `Cancel`

Only one inline row mode is active at a time (`view`, `edit-target`, or `confirm-delete`).

### Feedback

- Duplicate warning appears inline on config page.
- Edit/delete outcomes appear as flash messages on the athlete list view (home route).
- Messages are action-specific and non-ambiguous.

## Data and Identity Rules

Duplicate detection algorithm (deterministic):

1. If incoming `entry_id` is present, match by `(race_slug, entry_id)` only.
2. Else if incoming `entry_id` is absent and `bib` is present, match by `(race_slug, bib)`.
3. Else reject add as validation error (`missing identity`) and do not mutate storage.
4. If both identity fields are present but indicate conflicting existing records, return conflict error and do not mutate storage.

This ensures stable duplicate detection while still handling practical edge cases.

## Backend and Store Changes

## `AthleteStore` additions

- `find_by_identity(race_slug, entry_id=None, bib=None)` that applies the duplicate detection algorithm and returns either one match, no match, or conflict.
- `update_target_time(athlete_id, target_finish_time)` to support inline edit.
- `delete(athlete_id)` to support inline deletion.

## Route behavior

- `POST /config`
  - validates inputs
  - checks duplicate before `add`
  - duplicate returns config page with warning + link
  - missing identity or conflict returns config page with explicit validation/conflict warning
  - non-duplicate performs add and redirects home
- `POST /athlete/<id>/target`
  - validates `HH:MM:SS`
  - updates target for athlete id only when valid
  - invalid value performs no mutation and redirects home with error flash
  - redirects home with success/error flash
- `POST /athlete/<id>/delete`
  - requires explicit confirmation form field (for example `confirm=yes`)
  - deletes athlete by id only when confirmation is present and valid
  - missing/invalid confirmation performs no mutation and redirects home with warning flash
  - redirects home with success/error flash

## Validation and Errors

- Reuse existing `parse_hhmmss` validator for both add and edit target operations.
- Missing/stale athlete id on update/delete returns a user-safe flash warning, not a server error.
- Duplicate add attempts do not mutate existing records, including target time.

## Testing Strategy

### Storage tests

- Duplicate add is rejected by identity rule.
- Duplicate identity precedence follows `entry_id` first, then `bib` fallback only when `entry_id` is missing.
- Duplicate add does not mutate existing athlete rows.
- Missing-identity and conflict-identity paths return safe no-mutation outcomes.
- Update target time succeeds for valid id and value.
- Update target time handles missing id.
- Delete succeeds for valid id and handles missing id.

### Route tests

- `/config` duplicate case returns warning and list link.
- `/athlete/<id>/target` handles valid and invalid target inputs.
- `/athlete/<id>/delete` requires confirmation signal and handles stale id behavior.

### Template/UX tests

- Athlete list row renders edit/delete affordances.
- Athlete list row mode transitions preserve one active mode at a time.
- Duplicate warning appears on config response.
- Inline delete confirmation controls are present when row is in delete mode.

## Rationale

This design keeps the current app mental model intact:

- config page is for adding athletes
- athlete list is for managing already-added athletes

It minimizes clicks, keeps duplicate handling explicit, and introduces only small, testable backend extensions.
