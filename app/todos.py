import json
from datetime import datetime, timedelta
from io import BytesIO

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, send_file,
)
from flask_login import login_required, current_user

from .extensions import db
from .models import Todo, Tag

bp = Blueprint("todos", __name__, url_prefix="/todos")


# ---- helpers ----------------------------------------------------------

def _parse_dt(value):
    """Parse a value from an <input type=datetime-local>."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError:
        return None


def _next_due(due_date, recurrence):
    """Work out the next due date for a recurring todo."""
    if not due_date:
        return None
    if recurrence == "daily":
        return due_date + timedelta(days=1)
    if recurrence == "weekly":
        return due_date + timedelta(weeks=1)
    if recurrence == "monthly":
        month = due_date.month + 1
        year = due_date.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(due_date.day, 28)  # avoid month-length edge cases
        return due_date.replace(year=year, month=month, day=day)
    return None


def _get_owned_todo(todo_id):
    if not todo_id:
        return None
    return Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()


def _get_or_create_tags(names):
    tags = []
    for name in names:
        tag = Tag.query.filter_by(user_id=current_user.id, name=name).first()
        if not tag:
            tag = Tag(user_id=current_user.id, name=name)
            db.session.add(tag)
        tags.append(tag)
    return tags


# ---- routes -------------------------------------------------------------

@bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    tag = request.args.get("tag", "").strip()

    query = Todo.query.filter_by(user_id=current_user.id)

    if q:
        query = query.filter(Todo.title.ilike(f"%{q}%"))
    if tag:
        query = query.join(Todo.tags).filter(Tag.name == tag)

    todos = query.order_by(
        Todo.done.asc(), Todo.due_date.is_(None), Todo.due_date.asc()
    ).all()

    avail_tags_rows = (
        db.session.query(Tag.name, db.func.count(Todo.id))
        .join(Todo.tags)
        .filter(Todo.user_id == current_user.id)
        .group_by(Tag.name)
        .all()
    )
    avail_tags = [{"name": n, "cnt": c} for n, c in avail_tags_rows]

    return render_template(
        "todos.html", todos=todos, avail_tags=avail_tags, q=q, tag=tag,
    )


@bp.route("/action", methods=["POST"])
@login_required
def action():
    act = request.form.get("action")

    if act == "create":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "error")
            return redirect(url_for("todos.index"))

        due = _parse_dt(request.form.get("due"))
        reminder = _parse_dt(request.form.get("reminder"))
        recurrence = request.form.get("recurrence") or None
        tag_names = [
            t.strip() for t in request.form.get("tags", "").split(",") if t.strip()
        ]

        todo = Todo(
            user_id=current_user.id, title=title, due_date=due,
            reminder_at=reminder, recurrence=recurrence,
        )
        todo.tags = _get_or_create_tags(tag_names)
        db.session.add(todo)
        db.session.commit()

    elif act == "toggle":
        todo = _get_owned_todo(request.form.get("id"))
        if todo:
            todo.done = not todo.done
            # spin off the next occurrence when a recurring todo is completed
            if todo.done and todo.recurrence and todo.due_date:
                next_due = _next_due(todo.due_date, todo.recurrence)
                clone = Todo(
                    user_id=current_user.id, title=todo.title, due_date=next_due,
                    recurrence=todo.recurrence,
                )
                clone.tags = list(todo.tags)
                db.session.add(clone)
            db.session.commit()

    elif act == "delete":
        todo = _get_owned_todo(request.form.get("id"))
        if todo:
            db.session.delete(todo)
            db.session.commit()

    return redirect(url_for("todos.index"))


@bp.route("/export")
@login_required
def export_data():
    todos = Todo.query.filter_by(user_id=current_user.id).all()
    data = [
        {
            "title": t.title,
            "done": t.done,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "reminder_at": t.reminder_at.isoformat() if t.reminder_at else None,
            "recurrence": t.recurrence,
            "tags": [tg.name for tg in t.tags],
        }
        for t in todos
    ]
    buf = BytesIO(json.dumps(data, indent=2).encode("utf-8"))
    return send_file(
        buf, mimetype="application/json", as_attachment=True,
        download_name="todos_export.json",
    )


@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_data():
    message = None
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            message = "Please choose a file."
        else:
            try:
                data = json.load(file.stream)
                for item in data:
                    due = (
                        datetime.fromisoformat(item["due_date"])
                        if item.get("due_date") else None
                    )
                    reminder = (
                        datetime.fromisoformat(item["reminder_at"])
                        if item.get("reminder_at") else None
                    )
                    todo = Todo(
                        user_id=current_user.id,
                        title=item.get("title", "Untitled"),
                        done=bool(item.get("done", False)),
                        due_date=due,
                        reminder_at=reminder,
                        recurrence=item.get("recurrence"),
                    )
                    todo.tags = _get_or_create_tags(item.get("tags", []))
                    db.session.add(todo)
                db.session.commit()
                return redirect(url_for("todos.index"))
            except Exception:
                message = "Could not read that file. Make sure it's a valid export from this app."

    return render_template("import.html", message=message)
