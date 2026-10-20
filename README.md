# Streaklight

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3119/)
[![Flask 3.0](https://img.shields.io/badge/Flask-3.0-black.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](/LICENSE)

Streaklight is a focused habit tracker built with Flask, Jinja templates, and SQLite. It helps you stay consistent with simple daily check-ins, clear streak metrics, and a 10-week heatmap that shows momentum at a glance.

Live app: https://streaklight.vercel.app

## Features

- Account registration, login, and logout
- Secure password hashing with Werkzeug
- User-scoped habit data access
- Create habits with one of five accent colors: moss, gold, slate, brick, plum
- Daily check-in toggle per habit
- Current streak and best streak tracking
- 10-week Monday-Sunday dashboard heatmap
- Habit deletion
- Flash messages and responsive server-rendered UI

## How it works

### Request flow

1. A browser request hits Flask routes in `app.py`.
2. Flask reads/writes SQLite through Python's `sqlite3` module (with foreign keys enabled).
3. Route handlers compute dashboard values (streaks + heatmap).
4. Flask renders Jinja templates in `templates/` and returns HTML.

Vercel traffic is routed to `api/index.py`, which imports `app` from `app.py`.

### Streak and heatmap behavior

- `compute_streak()` keeps today's streak "open": if you have not checked in today, it counts from yesterday backward.
- `compute_best_streak()` finds the longest historical consecutive run.
- `build_heatmap()` generates Monday-Sunday columns and the dashboard renders 10 weeks (`weeks=10`).

## Project structure

```text
Streaklight/
├── app.py
├── api/
│   └── index.py
├── static/
│   └── styles.css
├── templates/
│   ├── index.html
│   ├── layout.html
│   ├── login.html
│   └── register.html
├── .devcontainer/
│   └── devcontainer.json
├── .env.example
├── LICENSE
├── Procfile
├── README.md
├── requirements.txt
├── runtime.txt
└── vercel.json
```

## Prerequisites

- Python 3.11
- `pip`

## Local setup

```bash
# 1) Install dependencies
pip install -r requirements.txt

# 2) (Optional) configure environment variables
cp .env.example .env
# then set STREAKLIGHT_SECRET and/or DATABASE_PATH

# 3) Run the app
python3 app.py
```

Open: http://127.0.0.1:5000

Notes:
- The database is initialized automatically by `init_db()` in `app.py`.
- Without `DATABASE_PATH`, local default is `streaklight.db` in the project root.
- Set `FLASK_DEBUG=1` for local debug mode.

## Deployment

### Gunicorn (production process)

```bash
gunicorn app:app
```

`Procfile` already defines:

```text
web: gunicorn app:app
```

### Render

1. Create a web service from this repository.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app`
4. Set environment variables (`STREAKLIGHT_SECRET`, `DATABASE_PATH`).
5. Attach persistent storage for the SQLite file path.

### Vercel

- `vercel.json` routes all traffic to `api/index.py` using `@vercel/python`.
- Set `STREAKLIGHT_SECRET` in project environment variables.
- If `DATABASE_PATH` is not set on Vercel, app defaults to `/tmp/streaklight.db`.

> ⚠️ **Important:** Vercel serverless filesystem storage (`/tmp`) is not durable. Production data can be reset between invocations/deployments. Use persistent storage on Render or move to a hosted database for durable production data.

## Configuration

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `STREAKLIGHT_SECRET` | Recommended in all environments | `dev-secret-change-me` (fallback in code) | Use a long random value in production for secure sessions. |
| `DATABASE_PATH` | Optional | Local: `streaklight.db` near `app.py`; Vercel: `/tmp/streaklight.db` | Set to persistent storage path in production. |
| `FLASK_DEBUG` | Optional | Off (`0`/unset) | Set to `1` for local debug mode. |

## Security and data notes

- Passwords are hashed and verified with Werkzeug (`generate_password_hash` / `check_password_hash`).
- Sessions use Flask signed cookies with `HTTPOnly` and `SameSite=Lax` settings.
- SQL queries are parameterized and habit operations are user-scoped.
- For production, set a strong `STREAKLIGHT_SECRET` and use persistent storage (or a hosted database).

## Development and testing

There is currently no automated test suite in this repository.

Recommended manual verification flow:
1. Register a new account.
2. Log in and create habits with different colors.
3. Toggle daily check-ins and confirm streak/best-streak updates.
4. Confirm 10-week heatmap updates as expected.
5. Delete a habit and verify associated check-ins are removed.
6. Log out and verify protected dashboard access redirects to login.

## Roadmap

- Weekly/custom-frequency habits
- Reminder emails
- Year-in-review export

## License

Licensed under the MIT License. See [LICENSE](/LICENSE).

Copyright (c) 2026 Priyansh Dhakrey.
