# Half-Iron Target Run Pace

Flask app for tracking configured athletes in a target race and computing run-leg pacing guidance from live RTRT splits.

## v1 Scope

- Race focus: Ironman 70.3 Rockford (extensible architecture for future races)
- Configure athletes with target finish times
- Search athletes from RTRT race data
- View latest split details
- If athlete reached T2, compute required half marathon time + required min/mi pace
- If run splits exist, show ahead/behind target run pace

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set credentials.
4. Start app:
   - `flask --app app run --debug`

## Test

- `pytest`

## Deployment Notes

- Primary target: Flask hosting (Render/Fly.io/PythonAnywhere/etc.).
- GitHub Pages cannot run Flask server code directly; static-only publishing would require a separate API/proxy layer.
