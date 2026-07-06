package handlers

import (
	"context"
	"html/template"
	"net/http"
	"todo-app/internal/session"
	"todo-app/internal/store"
)

type Handler struct {
	userStore  *store.UserStore
	todoStore  *store.TodoStore
	session    *session.CookieSessionStore
	templates  *template.Template
}

func New(userStore *store.UserStore, todoStore *store.TodoStore, sessionStore *session.CookieSessionStore) *Handler {
	// Explicitly list base + each page template
	tmpl := template.Must(template.ParseFiles(
		"templates/base.html",
		"templates/home.html",
		"templates/login.html",
		"templates/register.html",
		"templates/todos.html",
	))

	return &Handler{
		userStore:  userStore,
		todoStore:  todoStore,
		session:    sessionStore,
		templates:  tmpl,
	}
}

func (h *Handler) requireAuth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		userID, ok := h.session.Get(r)
		if !ok {
			http.Redirect(w, r, "/login", http.StatusSeeOther)
			return
		}
		next(w, r.WithContext(context.WithValue(r.Context(), "userID", userID)))
	}
}

func (h *Handler) getUserID(r *http.Request) int64 {
	return r.Context().Value("userID").(int64)
}