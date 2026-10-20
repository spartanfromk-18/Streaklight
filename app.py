import sqlite3
import os
from datetime import date, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
DEBUG = os.environ.get("FLASK_DEBUG") == "1"
secret_key = os.environ.get("STREAKLIGHT_SECRET")
if secret_key is None:
    secret_key = "dev-secret-change-me"
    print("Warning: STREAKLIGHT_SECRET is not set; using the development secret key.")
app.secret_key = secret_key
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=not DEBUG,
)
configured_database_path = os.environ.get("DATABASE_PATH")
if configured_database_path:
    DB_PATH = configured_database_path
elif os.environ.get("VERCEL") == "1":
    DB_PATH = "/tmp/streaklight.db"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "streaklight.db")

HABIT_COLORS = ["moss", "gold", "slate", "brick", "plum"]


# ---------- Database helpers ----------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT 'moss',
            created_at TEXT NOT NULL DEFAULT (date('now')),
            archived INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            UNIQUE(habit_id, day),
            FOREIGN KEY (habit_id) REFERENCES habits(id)
        );
        """
    )
    db.commit()
    db.close()


init_db()


# ---------- Auth helpers ----------

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped


# ---------- Streak + heatmap logic ----------

def get_checkin_days(db, habit_id):
    rows = db.execute(
        "SELECT day FROM checkins WHERE habit_id = ?", (habit_id,)
    ).fetchall()
    return {r["day"] for r in rows}


def compute_streak(days_set):
    """Current streak counting back from today, allowing today to still be open."""
    today = date.today()
    streak = 0
    cursor = today
    # If today isn't checked in yet, streak still counts from yesterday backwards.
    if today.isoformat() not in days_set:
        cursor = today - timedelta(days=1)
    while cursor.isoformat() in days_set:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def compute_best_streak(days_set):
    if not days_set:
        return 0
    ordered = sorted(date.fromisoformat(d) for d in days_set)
    best = run = 1
    for prev, curr in zip(ordered, ordered[1:]):
        if (curr - prev).days == 1:
            run += 1
        else:
            run = 1
        best = max(best, run)
    return best


def build_heatmap(days_set, weeks=14):
    """Return a list of weeks, each a list of 7 (date_iso, checked) tuples, oldest first."""
    today = date.today()
    start = today - timedelta(days=today.weekday())  # Monday of current week
    start -= timedelta(weeks=weeks - 1)
    grid = []
    cursor = start
    for _ in range(weeks):
        week = []
        for _ in range(7):
            iso = cursor.isoformat()
            week.append((iso, iso in days_set, cursor <= today))
            cursor += timedelta(days=1)
        grid.append(week)
    return grid


# ---------- Routes ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not username or not password:
            flash("Enter a username and password.", "error")
            return render_template("register.html")
        if password != confirmation:
            flash("Passwords don't match.", "error")
            return render_template("register.html")

        db = get_db()
        existing = db.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            flash("That username is taken.", "error")
            return render_template("register.html")

        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        db.commit()
        user = db.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        session["user_id"] = user["id"]
        session["username"] = username
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user is None or not check_password_hash(user["hash"], password):
            flash("Wrong username or password.", "error")
            return render_template("login.html")

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    db = get_db()
    habits = db.execute(
        "SELECT * FROM habits WHERE user_id = ? AND archived = 0 ORDER BY created_at",
        (session["user_id"],),
    ).fetchall()

    habit_cards = []
    today_iso = date.today().isoformat()
    for h in habits:
        days = get_checkin_days(db, h["id"])
        habit_cards.append({
            "id": h["id"],
            "name": h["name"],
            "color": h["color"],
            "streak": compute_streak(days),
            "best": compute_best_streak(days),
            "checked_today": today_iso in days,
            "heatmap": build_heatmap(days, weeks=10),
        })

    return render_template("index.html", habits=habit_cards, colors=HABIT_COLORS)


@app.route("/habits", methods=["POST"])
@login_required
def add_habit():
    name = request.form.get("name", "").strip()
    color = request.form.get("color", "moss")
    if not name:
        flash("Give the habit a name.", "error")
        return redirect(url_for("index"))
    if color not in HABIT_COLORS:
        color = "moss"

    db = get_db()
    db.execute(
        "INSERT INTO habits (user_id, name, color) VALUES (?, ?, ?)",
        (session["user_id"], name, color),
    )
    db.commit()
    return redirect(url_for("index"))


@app.route("/habits/<int:habit_id>/delete", methods=["POST"])
@login_required
def delete_habit(habit_id):
    db = get_db()
    habit = db.execute(
        "SELECT * FROM habits WHERE id = ? AND user_id = ?",
        (habit_id, session["user_id"]),
    ).fetchone()
    if habit is None:
        flash("Habit not found.", "error")
        return redirect(url_for("index"))

    db.execute("DELETE FROM checkins WHERE habit_id = ?", (habit_id,))
    db.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    db.commit()
    return redirect(url_for("index"))


@app.route("/habits/<int:habit_id>/checkin", methods=["POST"])
@login_required
def checkin(habit_id):
    db = get_db()
    habit = db.execute(
        "SELECT * FROM habits WHERE id = ? AND user_id = ?",
        (habit_id, session["user_id"]),
    ).fetchone()
    if habit is None:
        flash("Habit not found.", "error")
        return redirect(url_for("index"))

    today_iso = date.today().isoformat()
    already = db.execute(
        "SELECT id FROM checkins WHERE habit_id = ? AND day = ?",
        (habit_id, today_iso),
    ).fetchone()

    if already:
        db.execute("DELETE FROM checkins WHERE id = ?", (already["id"],))
    else:
        db.execute(
            "INSERT INTO checkins (habit_id, day) VALUES (?, ?)",
            (habit_id, today_iso),
        )
    db.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=DEBUG)
