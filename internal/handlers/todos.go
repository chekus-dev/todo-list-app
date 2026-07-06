package handlers

import (
	"net/http"
	"strconv"
	"todo-app/internal/store"
)

type TodoPageData struct {
	Todos []store.Todo
	Error string
}

func (h *Handler) Todos(w http.ResponseWriter, r *http.Request) {
	h.requireAuth(h.todosHandler)(w, r)
}

func (h *Handler) todosHandler(w http.ResponseWriter, r *http.Request) {
	userID := h.getUserID(r)

	if r.Method == http.MethodPost {
		action := r.FormValue("action")
		switch action {
		case "create":
			title := r.FormValue("title")
			if title != "" {
				_, _ = h.todoStore.Create(userID, title)
			}
		case "toggle":
			idStr := r.FormValue("id")
			if id, err := strconv.ParseInt(idStr, 10, 64); err == nil {
				_ = h.todoStore.ToggleDone(id, userID)
			}
		case "delete":
			idStr := r.FormValue("id")
			if id, err := strconv.ParseInt(idStr, 10, 64); err == nil {
				_ = h.todoStore.Delete(id, userID)
			}
		}
		http.Redirect(w, r, "/todos", http.StatusSeeOther)
		return
	}

	todos, err := h.todoStore.ListByUser(userID)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	data := TodoPageData{Todos: todos}
	_ = h.templates.ExecuteTemplate(w, "todos.html", data)
}
