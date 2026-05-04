# Athlete Management Consistency Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add duplicate-safe athlete configuration plus inline target-edit and delete controls in athlete list, with server-side validation and regression tests.

**Architecture:** Keep `Configure Athlete` as add-only, enforce duplicate detection in `AthleteStore` and `POST /config`, and move management actions to list-row forms on `home`. Add dedicated POST routes for update/delete and keep feedback consistent via flashes on the home route.

**Tech Stack:** Python, Flask, Jinja templates, pytest

---

## File Structure

- Modify: `src/storage.py` (identity lookup, duplicate-safe add, update, delete)
- Modify: `app.py` (duplicate check in config flow, update/delete routes, flash messages)
- Modify: `templates/config.html` (duplicate warning + CTA link)
- Modify: `templates/index.html` (inline edit target + inline delete confirmation forms)
- Modify: `static/styles.css` (small styles for inline row controls and warnings if needed)
- Modify: `tests/test_web_ux.py` (route + rendered UX behavior)
- Create: `tests/test_storage.py` (store behavior for duplicate identity/update/delete)

## Chunk 1: Storage Identity and Mutations

### Task 1: Add deterministic athlete identity behavior in store

**Files:**
- Modify: `src/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write failing tests for storage identity logic**

```python
def test_add_rejects_duplicate_by_race_and_entry_id(): ...
def test_find_by_identity_falls_back_to_bib_when_entry_missing(): ...
def test_find_by_identity_prioritizes_entry_id_when_both_present(): ...
def test_add_rejects_missing_identity(): ...
def test_add_rejects_conflicting_identity_matches(): ...
def test_duplicate_attempt_does_not_mutate_existing_row(): ...
def test_update_target_time_updates_existing_row(): ...
def test_update_target_time_returns_none_for_unknown_id(): ...
def test_delete_removes_existing_row(): ...
def test_delete_returns_none_for_unknown_id(): ...
```

- [ ] **Step 2: Run storage tests and verify RED**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL due to missing methods/duplicate checks.

- [ ] **Step 3: Implement minimal storage methods**

```python
def find_by_identity(self, race_slug: str, entry_id: str | None = None, bib: str | None = None) -> dict:
    # returns {"status": "none" | "match" | "conflict", "athlete": dict | None}
    ...
def update_target_time(self, athlete_id: str, target_finish_time: str) -> dict | None: ...
def delete(self, athlete_id: str) -> dict | None: ...
def add(...):  # reject duplicate/conflict/missing identity with ValueError
```

- [ ] **Step 4: Re-run storage tests and verify GREEN**

Run: `pytest tests/test_storage.py -v`
Expected: PASS.

## Chunk 2: Config Flow Duplicate Guard and New Routes

### Task 2: Enforce duplicate-safe add and list action endpoints

**Files:**
- Modify: `app.py`
- Test: `tests/test_web_ux.py`

- [ ] **Step 1: Write failing route tests**

```python
def test_config_duplicate_shows_warning_with_link(...): ...
def test_config_missing_identity_shows_validation_warning(...): ...
def test_config_conflicting_identity_shows_conflict_warning(...): ...
def test_update_target_route_updates_and_redirects_home(...): ...
def test_update_target_route_rejects_invalid_target(...): ...
def test_update_target_route_unknown_id_warns_and_does_not_mutate(...): ...
def test_delete_route_requires_confirmation(...): ...
def test_delete_route_removes_athlete_when_confirmed(...): ...
def test_delete_route_unknown_id_warns_and_does_not_mutate(...): ...
```

- [ ] **Step 2: Run targeted route tests and verify RED**

Run: `pytest tests/test_web_ux.py -v`
Expected: FAIL because routes/flows not present yet.

- [ ] **Step 3: Implement app route behavior**

```python
# app.py
# - in POST /config, detect duplicate before store.add and render config with duplicate CTA
# - in POST /config, handle missing-identity/conflict with explicit warnings and no mutation
# - add POST /athlete/<id>/target (parse_hhmmss validation + flash)
# - add POST /athlete/<id>/delete (confirm=yes required + flash)
```

- [ ] **Step 4: Re-run targeted route tests and verify GREEN**

Run: `pytest tests/test_web_ux.py -v`
Expected: PASS.

- [ ] **Step 5: Assert message specificity and no-mutation negative paths**

Ensure tests verify:
- distinct flash/warning text for duplicate, missing identity, conflict, invalid target, stale id, invalid confirmation
- target value and row count remain unchanged on all negative paths

## Chunk 3: List UI Controls and Integration Coverage

### Task 3: Add inline row edit/delete controls and UI assertions

**Files:**
- Modify: `templates/index.html`
- Modify: `templates/config.html`
- Modify: `static/styles.css` (if minimal styling needed)
- Modify: `tests/test_web_ux.py`

- [ ] **Step 1: Write failing template/UX assertions**

```python
def test_home_renders_edit_and_delete_row_actions(...): ...
def test_home_renders_inline_delete_confirmation_controls(...): ...
def test_config_duplicate_warning_includes_list_link(...): ...
def test_home_only_one_row_mode_active_at_a_time(...): ...
def test_home_cancel_mode_returns_row_to_view(...): ...
```

- [ ] **Step 2: Run targeted UX tests and verify RED**

Run: `pytest tests/test_web_ux.py -v`
Expected: FAIL due to missing controls/text.

- [ ] **Step 3: Implement minimal template updates**

```html
<!-- index.html -->
<form method="post" action="/athlete/{{ athlete.id }}/target">...</form>
<form method="post" action="/athlete/{{ athlete.id }}/delete">...</form>
<!-- confirm flag + cancel path -->
<!-- explicit mode state via query params (mode=edit|delete and athlete_id=<id>) -->
```

```html
<!-- config.html -->
{% if duplicate_athlete %}
  <!-- warning + link to home -->
{% endif %}
```

- [ ] **Step 4: Re-run targeted UX tests and verify GREEN**

Run: `pytest tests/test_web_ux.py -v`
Expected: PASS.

## Chunk 4: Final Verification

### Task 4: Full regression and cleanup

**Files:**
- Verify: `tests/test_storage.py`
- Verify: `tests/test_web_ux.py`
- Verify: `tests/` full suite

- [ ] **Step 1: Run full web + storage suite**

Run: `pytest tests/test_storage.py tests/test_web_ux.py -v`
Expected: PASS.

- [ ] **Step 2: Run full project test suite**

Run: `pytest -v`
Expected: PASS with no new failures.

- [ ] **Step 3: Confirm requirements checklist against design spec**

Cross-check `specs/2026-05-03-athlete-management-design.md`:
- duplicate add warning + no mutation
- edit target route + validation
- delete requires confirmation
- list row controls present
- stale-id update/delete warning behavior
- single active inline mode with cancel returning to view

