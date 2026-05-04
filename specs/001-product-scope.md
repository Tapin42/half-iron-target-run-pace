# Product Scope (v1)

## Objective

Provide a simple supporter-facing dashboard that tracks selected athletes in Ironman 70.3 Rockford and translates current split state into actionable run-leg pacing guidance against a target finish time.

## Primary Users

- Friends/family supporters tracking athletes live
- Coach/athlete support crew using pacing deltas for decisions

## User Stories

1. As a user, I can configure athletes with:
   - Display name
   - RTRT athlete identifier (or bib/name selected from search)
   - Target finish time (`HH:MM:SS`)
2. As a user, I can search race athletes from RTRT and choose one for configuration.
3. As a user, I can view a list of configured athletes on the main screen.
4. As a user, I can click an athlete to view latest split and pacing details.
5. As a user, when athlete has reached T2, I can see:
   - Required half marathon split time to hit finish goal
   - Required average run pace in min/mi
6. As a user, when run splits exist, I can see whether current run pace is ahead/behind goal run pace.

## Non-Goals (v1)

- Full race analytics suite
- User login/account management
- Multi-tenant cloud persistence
- Complex notifications or alerting
- Advanced observability stack

## v1 Success Criteria

- Configuration workflow is usable from browser
- Athlete lookup retrieves race participants from RTRT API
- Athlete details render without exposing API credentials to browser
- Core math outputs are test-covered and accurate for representative scenarios
