# RTRT Data Contract

> Current state: done

## Auth and Transport

- All RTRT requests are server-side HTTP `POST` requests.
- Credentials are sent as form fields:
  - `appid` from `RTRT_APPID`
  - `token` from `RTRT_TOKEN`
- Credentials are never rendered in HTML or sent to client JavaScript.

## Baseline Request Parameters

- `timesort=1`
- `nohide=1`
- `checksum=`
- `max=<page size>`
- `catloc=1`
- `cattotal=1`
- `units=standard`
- `source=webtracker`

## Rockford v1 Event

- Event key: `IRM-ROCKFORD703-2026`

## Endpoints Used in v1

1. Athlete Search (preferred):
   - `POST https://api.rtrt.me/events/{event_key}/search`
   - Body includes query field(s) and base auth params
2. Category split listing fallback/search source:
   - `POST https://api.rtrt.me/events/{event_key}/categories/{category}/splits/{split}`
   - `split` typically `FINISH` for broad participant list access
3. Athlete detail splits:
   - `POST https://api.rtrt.me/events/{event_key}/entries/{entry_id}/splits`
   - Fallback shape support if data is embedded in list payload

## Normalized Athlete Shape (internal)

```json
{
  "entry_id": "string",
  "bib": "string",
  "name": "string",
  "division": "string"
}
```

## Normalized Split Shape (internal)

```json
{
  "name": "T2",
  "time": "05:01:00",
  "seconds": 18060
}
```

## Error Behavior

- Upstream non-200 or malformed payload:
  - log server-side
  - return user-safe message on UI
- Missing split data:
  - show latest known split section with unavailable math status
- Missing credentials:
  - app starts, but routes that require RTRT return explicit config error

## Security Model

- Required env vars:
  - `RTRT_APPID`
  - `RTRT_TOKEN`
- Optional:
  - `ATHLETE_CONFIG_FILE` path for local JSON persistence
- No hardcoded secrets in repository.

## Decomposed Tasks

- `tasks/done/007-rtrt-client-auth-and-baseline-params.md`
- `tasks/done/008-rtrt-athlete-search-and-fallback-listing.md`
- `tasks/done/009-rtrt-athlete-splits-and-normalization.md`
- `tasks/done/010-rtrt-error-handling-and-security-guards.md`
