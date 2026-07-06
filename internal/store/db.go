package store

import "database/sql"

func NewUserStore(db *sql.DB) *UserStore {
	return &UserStore{db: db}
}

func NewTodoStore(db *sql.DB) *TodoStore {
	return &TodoStore{db: db}
}
