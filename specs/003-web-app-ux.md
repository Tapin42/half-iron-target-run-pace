# Web App UX (v1)

> Current state: done

## Layout

- Single-page feel with two primary areas:
  1. **Configuration panel** (top)
  2. **Configured athlete list + detail panel** (main body)

## Configuration Panel

Inputs:
- Search term (name or bib)
- Search results list from RTRT race data
- Selected athlete summary
- Target finish time input (`HH:MM:SS`)
- Save button

Behavior:
- Search performs server request to RTRT
- Selecting a search result fills hidden entry metadata
- Validation ensures target finish format and selected athlete presence

## Main Athlete List

- Shows saved athletes and target finish time
- Displays last-known split label/time snapshot
- Each athlete row links to detail view

## Athlete Detail Card

Sections:
1. Athlete identity (name/bib/division)
2. Latest split
3. T2-driven calculation output:
   - target run time
   - required half-marathon completion time
   - required pace (min/mi)
4. Run progress status:
   - ahead/behind goal pace with signed seconds delta

## Refresh Model

- v1: manual refresh action per athlete detail page
- Future: configurable polling/auto-refresh

## Whiteboard-Friendly Output

- Keep numeric outputs large and explicit
- Favor plain language labels over abbreviations
- Display both `HH:MM:SS` and pace when relevant

## Decomposed Tasks

- `tasks/done/011-web-ux-config-panel-and-search-interactions.md`
- `tasks/done/012-web-ux-config-validation-and-athlete-list.md`
- `tasks/done/013-web-ux-athlete-detail-sections-and-math-presentation.md`
- `tasks/done/014-web-ux-refresh-action-and-whiteboard-output-polish.md`
