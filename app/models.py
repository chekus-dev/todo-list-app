from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db, login_manager

# Many-to-many link between todos and tags
todo_tags = db.Table(
    "todo_tags",
    db.Column("todo_id", db.Integer, db.ForeignKey("todo.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    theme = db.Column(db.String(10), default="dark", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    todos = db.relationship(
        "Todo", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_user_tag"),)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    done = db.Column(db.Boolean, default=False, nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    reminder_at = db.Column(db.DateTime, nullable=True)
    reminded = db.Column(db.Boolean, default=False, nullable=False)
    recurrence = db.Column(db.String(20), nullable=True)  # daily, weekly, monthly
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tags = db.relationship("Tag", secondary=todo_tags, backref="todos", lazy="joined")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
