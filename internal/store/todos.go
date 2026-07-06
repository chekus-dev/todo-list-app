package store

import (
	"database/sql"
	"time"
)

type Todo struct {
	ID        int64
	UserID    int64
	Title     string
	Done      bool
	CreatedAt time.Time
}

type TodoStore struct {
	db *sql.DB
}

func (s *TodoStore) Create(userID int64, title string) (*Todo, error) {
	t := &Todo{}
	err := s.db.QueryRow(
		`INSERT INTO todos (user_id, title, done, created_at)
		 VALUES ($1, $2, false, now()) RETURNING id, created_at`,
		userID, title,
	).Scan(&t.ID, &t.CreatedAt)
	if err != nil {
		return nil, err
	}
	t.UserID = userID
	t.Title = title
	t.Done = false
	return t, nil
}

func (s *TodoStore) ListByUser(userID int64) ([]Todo, error) {
	rows, err := s.db.Query(
		`SELECT id, user_id, title, done, created_at FROM todos
		 WHERE user_id = $1 ORDER BY created_at DESC`,
		userID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var todos []Todo
	for rows.Next() {
		var t Todo
		if err := rows.Scan(&t.ID, &t.UserID, &t.Title, &t.Done, &t.CreatedAt); err != nil {
			return nil, err
		}
		todos = append(todos, t)
	}
	return todos, rows.Err()
}

func (s *TodoStore) ToggleDone(id, userID int64) error {
	_, err := s.db.Exec(
		`UPDATE todos SET done = NOT done WHERE id = $1 AND user_id = $2`,
		id, userID,
	)
	return err
}

func (s *TodoStore) Delete(id, userID int64) error {
	_, err := s.db.Exec(
		`DELETE FROM todos WHERE id = $1 AND user_id = $2`,
		id, userID,
	)
	return err
}
