# Deployment Notes

## Primary Deployment: Flask App Hosting

Use a Python-capable host (Render, Fly.io, Railway, PythonAnywhere, etc.).

Minimum runtime requirements:
- Python 3.11+
- `pip install -r requirements.txt`
- Entrypoint serving Flask app from `app:app` (via Gunicorn or host-native Flask support)

Required environment variables:
- `RTRT_APPID`
- `RTRT_TOKEN`
- `FLASK_SECRET_KEY`
- Optional: `RTRT_EVENT_KEY`, `RTRT_SEARCH_CATEGORY`, `RTRT_FINISH_SPLIT`
- Optional: `ATHLETE_CONFIG_FILE` (if changing local JSON path)

## GitHub Pages Limitation

GitHub Pages is static hosting only and cannot execute Flask routes or server-side RTRT API requests.

If publishing UI on GitHub Pages, you would still need:
- A separate backend API deployment for RTRT calls and calculations
- A secure server-side secret store for `RTRT_APPID` and `RTRT_TOKEN`
- CORS/proxy integration between static frontend and backend

For this project, Flask hosting remains the recommended production path.
