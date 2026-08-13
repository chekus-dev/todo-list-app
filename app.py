import os
import sqlite3
import json
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    jsonify,
    send_file,
    Response,
)
from werkzeug.security import check_password_hash, generate_password_hash
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

DB_PATH = os.path.join(os.path.dirname(__file__), "todo.db")


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


def _add_months(dt, months):
    # naive month add that keeps day where possible
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, [31, 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return dt.replace(year=year, month=month, day=day)


def init_db():
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    # create base tables if they don't exist
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            due_date TEXT,
            reminder_at TEXT,
            reminded INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS todo_tags (
            todo_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (todo_id, tag_id),
            FOREIGN KEY (todo_id) REFERENCES todos (id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
        );
        """
    )

    # Ensure legacy databases gain the new 'recurrence' column if missing
    cols = [r[1] for r in cur.execute("PRAGMA table_info('todos')").fetchall()]
    if "recurrence" not in cols:
        try:
            cur.execute("ALTER TABLE todos ADD COLUMN recurrence TEXT")
        except Exception:
            # best-effort: ignore if alter fails
            pass

    db.commit()
    cur.close()
    db.close()


# ---------- Auth helpers ----------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_auth_state():
    return {"logged_in": bool(session.get("user_id")), "user_email": session.get("user_email")}


# ---------- Utility ----------

def _parse_dt(s):
    if not s:
        return None
    try:
        # Accept both full ISO and browser datetime-local (no timezone)
        return datetime.fromisoformat(s)
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%dT%H:%M")
        except Exception:
            return None


def _format_dt(dt):
    if not dt:
        return None
    return dt.isoformat()


# ---------- Routes ----------

@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("todos"))
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            error = "Email and password are required."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            db = get_db()
            existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                error = "An account with that email already exists."
            else:
                db.execute(
                    "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                    (email, generate_password_hash(password), datetime.utcnow().isoformat()),
                )
                db.commit()
                user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
                session["user_id"] = user["id"]
                session["user_email"] = email
                return redirect(url_for("todos"))

    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Invalid email or password."
        else:
            session["user_id"] = user["id"]
            session["user_email"] = user["email"]
            return redirect(url_for("todos"))

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/todos", methods=["GET"])
@login_required
def todos():
    db = get_db()
    user_id = session["user_id"]

    # Filters
    q = request.args.get("q")
    tag = request.args.get("tag")

    params = [user_id]
    base_sql = "SELECT todos.* FROM todos"

    if tag:
        base_sql += " JOIN todo_tags tt ON todos.id = tt.todo_id JOIN tags tg ON tg.id = tt.tag_id"
    where_clauses = ["todos.user_id = ?"]

    if q:
        where_clauses.append("todos.title LIKE ?")
        params.append(f"%{q}%")

    if tag:
        where_clauses.append("tg.name = ?")
        params.append(tag)

    where_sql = " WHERE " + " AND ".join(where_clauses)
    order_sql = " ORDER BY done ASC, created_at DESC"

    rows = db.execute(base_sql + where_sql + order_sql, params).fetchall()

    # load tags mapping for displayed todos
    todo_ids = [r["id"] for r in rows]
    tags_map = {}
    if todo_ids:
        placeholders = ",".join(["?"] * len(todo_ids))
        tag_rows = db.execute(
            f"SELECT tt.todo_id as todo_id, tg.name as name FROM tags tg JOIN todo_tags tt ON tg.id = tt.tag_id WHERE tt.todo_id IN ({placeholders})",
            todo_ids,
        ).fetchall()
        for tr in tag_rows:
            tags_map.setdefault(tr["todo_id"], []).append(tr["name"])

    # available tags for filter dropdown (only tags the user has)
    avail_tags = db.execute(
        "SELECT tg.name, COUNT(*) as cnt FROM tags tg JOIN todo_tags tt ON tg.id = tt.tag_id JOIN todos t ON t.id = tt.todo_id WHERE t.user_id = ? GROUP BY tg.name",
        (user_id,),
    ).fetchall()

    return render_template("todos.html", todos=rows, tags_map=tags_map, avail_tags=avail_tags, q=q, tag=tag)


@app.route("/todos", methods=["POST"])
@login_required
def todos_action():
    db = get_db()
    action = request.form.get("action")
    user_id = session["user_id"]

    if action == "create":
        title = request.form.get("title", "").strip()
        due = request.form.get("due")
        reminder = request.form.get("reminder")
        # Default missing due/reminder to current datetime (UTC)
        if not due:
            due = datetime.utcnow().isoformat()
        if not reminder:
            reminder = datetime.utcnow().isoformat()
        recurrence = request.form.get("recurrence") or None
        tags_raw = request.form.get("tags") or ""
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        if title:
            cur = db.execute(
                "INSERT INTO todos (user_id, title, due_date, reminder_at, recurrence, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, title, due, reminder, recurrence, datetime.utcnow().isoformat()),
            )
            todo_id = cur.lastrowid
            # attach tags
            for t in tags:
                tag_row = db.execute("SELECT id FROM tags WHERE name = ?", (t,)).fetchone()
                if tag_row:
                    tag_id = tag_row["id"]
                else:
                    res = db.execute("INSERT INTO tags (name) VALUES (?)", (t,))
                    tag_id = res.lastrowid
                try:
                    db.execute("INSERT INTO todo_tags (todo_id, tag_id) VALUES (?, ?)", (todo_id, tag_id))
                except sqlite3.IntegrityError:
                    pass
            db.commit()

    elif action == "toggle":
        todo_id = request.form.get("id")
        # load todo
        todo = db.execute("SELECT * FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id)).fetchone()
        if not todo:
            return redirect(url_for("todos"))
        new_done = 0 if todo["done"] else 1
        db.execute("UPDATE todos SET done = ? WHERE id = ? AND user_id = ?", (new_done, todo_id, user_id))
        db.commit()

        # If marking done and recurring, create next occurrence
        if new_done == 1 and todo["recurrence"]:
            try:
                due_dt = _parse_dt(todo["due_date"]) if todo["due_date"] else None
                rem_dt = _parse_dt(todo["reminder_at"]) if todo["reminder_at"] else None
                freq = todo["recurrence"]
                next_due = None
                next_rem = None
                if freq == "daily":
                    if due_dt:
                        next_due = due_dt + timedelta(days=1)
                    if rem_dt:
                        next_rem = rem_dt + timedelta(days=1)
                elif freq == "weekly":
                    if due_dt:
                        next_due = due_dt + timedelta(weeks=1)
                    if rem_dt:
                        next_rem = rem_dt + timedelta(weeks=1)
                elif freq == "monthly":
                    if due_dt:
                        next_due = _add_months(due_dt, 1)
                    if rem_dt:
                        next_rem = _add_months(rem_dt, 1)

                if next_due or next_rem:
                    cur = db.execute(
                        "INSERT INTO todos (user_id, title, due_date, reminder_at, recurrence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            user_id,
                            todo["title"],
                            _format_dt(next_due) if next_due else None,
                            _format_dt(next_rem) if next_rem else None,
                            todo["recurrence"],
                            datetime.utcnow().isoformat(),
                        ),
                    )
                    new_todo_id = cur.lastrowid
                    # copy tags
                    tag_rows = db.execute("SELECT tag_id FROM todo_tags WHERE todo_id = ?", (todo_id,)).fetchall()
                    for tr in tag_rows:
                        try:
                            db.execute("INSERT INTO todo_tags (todo_id, tag_id) VALUES (?, ?)", (new_todo_id, tr["tag_id"]))
                        except sqlite3.IntegrityError:
                            pass
                    db.commit()
            except Exception:
                # don't block toggle if recurrence processing fails
                pass

    elif action == "delete":
        todo_id = request.form.get("id")
        db.execute("DELETE FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id))
        db.commit()

    return redirect(url_for("todos"))


# ---------- Export / Import ----------

@app.route("/export")
@login_required
def export_data():
    db = get_db()
    user_id = session["user_id"]
    todos = db.execute("SELECT * FROM todos WHERE user_id = ?", (user_id,)).fetchall()
    todo_list = []
    for t in todos:
        todo_list.append({k: t[k] for k in t.keys()})
    data = json.dumps({"todos": todo_list}, indent=2)
    buf = BytesIO()
    buf.write(data.encode())
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="todos.json", mimetype="application/json")


@app.route("/import", methods=["GET", "POST"])
@login_required
def import_data():
    db = get_db()
    user_id = session["user_id"]
    message = None
    if request.method == "POST":
        uploaded = request.files.get("file")
        if not uploaded:
            message = "No file uploaded"
        else:
            try:
                payload = json.load(uploaded.stream)
                todos = payload.get("todos", [])
                for t in todos:
                    db.execute(
                        "INSERT INTO todos (user_id, title, done, due_date, reminder_at, recurrence, reminded, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            user_id,
                            t.get("title", ""),
                            int(bool(t.get("done", 0))),
                            t.get("due_date"),
                            t.get("reminder_at"),
                            t.get("recurrence"),
                            int(bool(t.get("reminded", 0))),
                            datetime.utcnow().isoformat(),
                        ),
                    )
                db.commit()
                message = "Import completed."
            except Exception as e:
                message = f"Import failed: {e}"

    return render_template("import.html", message=message)


# ---------- REST API (session-authenticated) ----------

@app.route("/api/todos", methods=["GET", "POST"])
@login_required
def api_todos():
    db = get_db()
    user_id = session["user_id"]
    if request.method == "GET":
        rows = db.execute("SELECT * FROM todos WHERE user_id = ?", (user_id,)).fetchall()
        return jsonify([dict(r) for r in rows])

    data = request.get_json() or {}
    title = data.get("title")
    if not title:
        return jsonify({"error": "title required"}), 400
    due = data.get("due_date")
    reminder = data.get("reminder_at")
    recurrence = data.get("recurrence")
    # Default missing due/reminder to current datetime (UTC)
    if not due:
        due = datetime.utcnow().isoformat()
    if not reminder:
        reminder = datetime.utcnow().isoformat()
    cur = db.execute(
        "INSERT INTO todos (user_id, title, due_date, reminder_at, recurrence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, title, due, reminder, recurrence, datetime.utcnow().isoformat()),
    )
    db.commit()
    todo_id = cur.lastrowid
    return jsonify({"id": todo_id}), 201


@app.route("/api/todos/<int:todo_id>", methods=["GET", "PATCH", "DELETE"])
@login_required
def api_todo_detail(todo_id):
    db = get_db()
    user_id = session["user_id"]
    todo = db.execute("SELECT * FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id)).fetchone()
    if not todo:
        return jsonify({"error": "not found"}), 404

    if request.method == "GET":
        return jsonify(dict(todo))

    if request.method == "DELETE":
        db.execute("DELETE FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id))
        db.commit()
        return jsonify({}), 204

    # PATCH
    data = request.get_json() or {}
    fields = []
    params = []
    for k in ("title", "due_date", "reminder_at", "recurrence", "done", "reminded"):
        if k in data:
            fields.append(f"{k} = ?")
            params.append(data[k])
    if fields:
        params.extend([todo_id, user_id])
        db.execute(f"UPDATE todos SET {', '.join(fields)} WHERE id = ? AND user_id = ?", params)
        db.commit()
    return jsonify({})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
