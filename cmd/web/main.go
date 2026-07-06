package main

import (
	"database/sql"
	"log"
	"net/http"
	"time"

	"todo-app/internal/handlers"
	"todo-app/internal/store"
	"todo-app/internal/session"

	_ "github.com/mattn/go-sqlite3"
)

func main() {
	db, err := sql.Open("sqlite3", "todo.db")
	if err != nil {
		log.Fatal(err)
	}
	if err := db.Ping(); err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Create tables if not exist
	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS users (
			id            INTEGER PRIMARY KEY AUTOINCREMENT,
			email         TEXT NOT NULL UNIQUE,
			password_hash BLOB NOT NULL
		);
		CREATE TABLE IF NOT EXISTS todos (
			id         INTEGER PRIMARY KEY AUTOINCREMENT,
			user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
			title      TEXT NOT NULL,
			done       BOOLEAN NOT NULL DEFAULT 0,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
		);
	`)
	if err != nil {
		log.Fatal(err)
	}

	userStore := store.NewUserStore(db)
	todoStore := store.NewTodoStore(db)
	sessionStore := session.NewCookieSessionStore(
		[]byte("your-secret-key-change-in-prod"),
		30*24*time.Hour,
	)

	h := handlers.New(userStore, todoStore, sessionStore)

	mux := http.NewServeMux()

	mux.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir("static"))))

	mux.HandleFunc("/", h.Home)
	mux.HandleFunc("/login", h.Login)
	mux.HandleFunc("/logout", h.Logout)
	mux.HandleFunc("/register", h.Register)
	mux.HandleFunc("/todos", h.Todos)

	log.Println("Server starting on :8080")
	if err := http.ListenAndServe(":8080", mux); err != nil {
		log.Fatal(err)
	}
}