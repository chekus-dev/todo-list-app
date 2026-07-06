package store

import (
	"database/sql"
	"errors"
)

var ErrNotFound = errors.New("not found")

type User struct {
	ID       int64
	Email    string
	Password []byte
}

type UserStore struct {
	db *sql.DB
}

func (s *UserStore) Create(email string, password []byte) (*User, error) {
	var id int64
	err := s.db.QueryRow(
		`INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id`,
		email, password,
	).Scan(&id)
	if err != nil {
		return nil, err
	}
	return &User{ID: id, Email: email, Password: password}, nil
}

func (s *UserStore) GetByEmail(email string) (*User, error) {
	u := &User{}
	var pw []byte
	err := s.db.QueryRow(
		`SELECT id, email, password_hash FROM users WHERE email = $1`,
		email,
	).Scan(&u.ID, &u.Email, &pw)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, ErrNotFound
		}
		return nil, err
	}
	u.Password = pw
	return u, nil
}
