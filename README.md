# Todo App

A Flask todo app with auth, due dates, reminders, recurrence, tags, search, and JSON import/export.

## Structure

```
todo_app/
├── run.py                  # entry point
├── requirements.txt
└── app/
    ├── __init__.py          # app factory, registers blueprints
    ├── config.py             # config (reads SECRET_KEY, DATABASE_URL from env)
    ├── extensions.py         # db, login_manager instances
    ├── models.py              # User, Tag, Todo (SQLAlchemy)
    ├── main.py                 # home page blueprint
    ├── auth.py                  # register/login/logout blueprint
    ├── todos.py                  # todos CRUD, tags, import/export blueprint
    ├── settings.py                # theme, change email/password, delete account
    ├── templates/
    └── static/css/style.css
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

Visit http://127.0.0.1:5000 — the SQLite database (`todo.db`) is created automatically on first run.

## Notes

- Passwords are hashed with Werkzeug's `generate_password_hash`.
- Sessions are handled by Flask-Login.
- Recurring todos: marking one done automatically creates the next occurrence (daily/weekly/monthly).
- Mobile styling lives in `static/css/style.css` under the two `@media` blocks near the bottom.
- Theme (dark/light) is a per-user preference set on `/settings`, applied via a `data-theme` attribute on `<html>`.
- If you're upgrading from an earlier version of this project, delete `todo.db` so the new `theme` column on `User` gets created (there's no migration tool wired up here).
