# Streaklight

#### Video Demo: <add your YouTube link here before submitting>

#### Description

Streaklight is a habit-tracking web app built for CS50's final project. It lets a
person create an account, add the daily habits they want to build, check in on
each one once a day, and watch a streak counter and a growth heatmap build up
over time — the same visual idea as a GitHub contribution graph, but applied to
personal habits instead of commits.

The core idea I wanted to get right was **honesty about momentum**. A lot of
habit trackers either overcomplicate things with reminders, social feeds, and
gamified badges, or oversimplify to a single checkbox that resets to zero the
moment you miss a day and gives you no sense of your history. Streaklight sits
in between: one check-in button per habit, a current streak, a personal best
streak, and a compact heatmap of the last ten weeks so a single missed day
reads as a small gap in a longer pattern rather than a failure that erases
everything before it.

## How it works

The app is a Flask application backed by SQLite, with server-rendered Jinja
templates (no separate frontend framework, and no client-side state to keep in
sync with the database — every action is a form POST followed by a redirect,
which is deliberately simple and keeps the source of truth in one place).

**`app.py`** contains the whole backend:

- **Auth.** `/register` and `/login` handle account creation and sign-in.
  Passwords are never stored directly — `werkzeug.security.generate_password_hash`
  hashes them before they touch the database, and `check_password_hash` verifies
  on login. Sessions are Flask's signed cookie sessions; a `login_required`
  decorator protects every route that touches a user's own data, and every
  habit query is scoped with `WHERE user_id = ?` so one account can never read
  or modify another account's habits, even by guessing a habit's numeric id.
- **Habits.** `/habits` (POST) creates a habit with a name and one of five
  accent colors. `/habits/<id>/delete` removes a habit and its check-in
  history, guarded by a confirmation dialog in the UI so it isn't one
  accidental click.
- **Check-ins.** `/habits/<id>/checkin` is a toggle: POSTing it inserts
  today's date into the `checkins` table if it isn't there yet, or removes it
  if it is — so accidentally clicking "check in" twice doesn't do anything
  destructive, and undoing a mis-click is a second click rather than a support
  ticket.
- **Streak math.** `compute_streak()` walks backward day by day from today (or
  from yesterday, if today hasn't been checked in yet, so a streak doesn't
  visually "break" at 7am before you've had a chance to check in) counting
  consecutive checked-in days. `compute_best_streak()` scans the full sorted
  history for the longest run of consecutive days ever achieved, independent
  of the current streak. `build_heatmap()` builds a 10-week grid of Monday
  through Sunday columns so the template can render it as a grid of small
  squares without doing any date arithmetic itself.

**`templates/`** holds four Jinja templates: `layout.html` (shared shell —
nav bar, flash messages), `login.html` and `register.html` (matching auth
forms), and `index.html`, which is the dashboard: an "Add a habit" panel that
expands inline instead of navigating to a separate page, and a responsive grid
of habit cards, each showing the streak, best streak, heatmap, and a
context-aware check-in button (its label and color change once you've already
checked in today, so the state of the day is visible at a glance).

**`static/styles.css`** is the entire design system, written from scratch
rather than pulled from a UI kit, using CSS custom properties for a small
five-color "growing things" accent palette (moss, gold, slate, brick, plum)
that a user picks per habit, on a warm paper background — I wanted the app to
feel more like a notebook you keep than a corporate dashboard. Headings use
Fraunces, a display serif with some warmth to it, and everything else uses
Work Sans; both are loaded from Google Fonts. The layout is a single-column,
max-width page rather than a sidebar app shell, because with one page of real
content (the habit grid) a sidebar would just be empty most of the time.

## Design decisions and things I considered

- **Why SQLite and not the `cs50` Python library's SQL wrapper?** I used the
  standard library's `sqlite3` module directly with parameterized queries
  (`?` placeholders) so the project doesn't depend on CS50's own library and
  would run the same way on any machine with Flask installed — but the schema
  and query style will look familiar from the Finance problem set.
- **Why a toggle for check-ins instead of a separate "undo" flow?** Early on I
  had check-in as insert-only, but that meant a stray click on the wrong
  habit's button had no way back except deleting the whole habit. A toggle on
  the same button removes that failure mode for one extra `if` statement.
- **Why compute streaks in Python instead of SQL?** SQLite doesn't have a
  clean built-in way to find runs of consecutive dates, and the habit history
  size per user is small (at most a few thousand rows even after years of
  daily use), so walking the checked-in days in Python is simpler to read and
  test than a recursive CTE, at negligible cost.
- **What I'd add next.** Weekly/custom-frequency habits (not just daily),
  reminder emails, and exporting a year in review — all straightforward
  extensions of the existing `habits`/`checkins` schema, left out to keep this
  submission focused on one thing done well.

## Running it locally

```
pip install -r requirements.txt
python3 app.py
```

The first run creates `streaklight.db` automatically. Then visit
`http://127.0.0.1:5000`, register an account, and add a habit.

## Deploying

Run locally with:

```
pip install -r requirements.txt
python app.py
```

For a production process, start Gunicorn with:

```
gunicorn app:app
```

Set `STREAKLIGHT_SECRET` to a long random value in the deployment environment.
Set `DATABASE_PATH` to the SQLite file on persistent storage; it defaults to
`streaklight.db` beside `app.py`. `FLASK_DEBUG=1` enables debug mode for local
development only.

On Render, create a web service with build command
`pip install -r requirements.txt` and start command `gunicorn app:app`. Add
`STREAKLIGHT_SECRET` and `DATABASE_PATH` as environment variables, and attach
persistent storage for the directory containing the database file.

Vercel is also supported through the `api/index.py` serverless entrypoint. Add
`STREAKLIGHT_SECRET` in the Vercel project settings and deploy from the
repository root. Vercel's filesystem is temporary, so the SQLite database is
stored under `/tmp` there and can be reset between deployments or function
instances. Use Render with a persistent disk, or replace SQLite with a hosted
database, when durable production data is required.

## File structure

```
streaklight/
├── app.py                 Flask app: routes, auth, streak/heatmap logic
├── Procfile               Gunicorn start command
├── runtime.txt            Python runtime version
├── requirements.txt
├── .env.example           deployment environment variable names
├── api/
│   └── index.py            Vercel serverless entrypoint
├── templates/
│   ├── layout.html
│   ├── login.html
│   ├── register.html
│   └── index.html
└── static/
    └── styles.css
```
