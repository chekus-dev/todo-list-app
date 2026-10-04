# Todo App
<img width="1300" height="1216" alt="image" src="https://github.com/user-attachments/assets/8757c4f6-71f7-4e27-96ff-c697a1c472b5" />

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

## Hosting

This app is ready for any host that supports a Python web service. Set the `SECRET_KEY` environment variable, then use:

```bash
gunicorn run:app
```

The included `Procfile` uses that command. For a hosted database, set `DATABASE_URL` to a PostgreSQL connection string. Without it, the app uses local SQLite, which is suitable for development but may not persist across deploys on some platforms.

### Deployed  on Render
- live link https://todo-list-app-4-6mr8.onrender.com/


    - **Runtime:** Python 3
    - **Build Command:** `pip install -r requirements.txt`
    - **Start Command:** `gunicorn run:app`
    - **Instance Type:** Free or another plan

4. Add an environment variable named `SECRET_KEY` with a long random value.
5. Create a Render PostgreSQL database from **New +** → **PostgreSQL**.
6. Copy its **Internal Database URL** into the web service environment variable named `DATABASE_URL`.
7. Deploy the service. Render will provide the public `.onrender.com` URL.

Do not rely on the default SQLite database for production because files on some Render services are ephemeral. PostgreSQL keeps user accounts and todos across deploys.

## Notes

- Passwords are hashed with Werkzeug's `generate_password_hash`.
- Sessions are handled by Flask-Login.
- Recurring todos: marking one done automatically creates the next occurrence (daily/weekly/monthly).
- Mobile styling lives in `static/css/style.css` under the two `@media` blocks near the bottom.
- Theme (dark/light) is a per-user preference set on `/settings`, applied via a `data-theme` attribute on `<html>`.
- If you're upgrading from an earlier version of this project, delete `todo.db` so the new `theme` column on `User` gets created (there's no migration tool wired up here).
