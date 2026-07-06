package handlers

import (
	"fmt"
	"net/http"
	"strconv"
	
)

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

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Todos • Todo App</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header>
    <div class="inner">
      <a class="brand" href="/">Todo App</a>
      <nav>
        <a href="/todos">Todos</a>
        <a href="/logout">Logout</a>
      </nav>
    </div>
  </header>

  <div class="container">
    <div class="card">
      <h1>Your Todos</h1>

      <form method="post" action="/todos">
        <input name="action" type="hidden" value="create">
        <div>
          <label for="title">New todo</label>
          <input id="title" name="title" type="text" placeholder="Buy milk" required>
        </div>
        <div style="margin-top:0.75rem">
          <button type="submit">Add todo</button>
        </div>
      </form>
`)

	if len(todos) == 0 {
		fmt.Fprintln(w, `
      <p style="margin-top:1rem">No todos yet. Add your first one above.</p>
`)
	} else {
		fmt.Fprintln(w, `
      <ul class="todo-list">
`)
		for _, t := range todos {
			doneClass := ""
			if t.Done {
				doneClass = " todo-done"
			}
			fmt.Fprintf(w, `
        <li class="%s">
          <form method="post" action="/todos" class="todo-actions">
            <input name="action" type="hidden" value="toggle">
            <input name="id" type="hidden" value="%d">
            <button type="submit" class="btn-sm">%s</button>
          </form>
          <span class="todo-title">%s</span>
          <div class="todo-actions">
            <form method="post" action="/todos">
              <input name="action" type="hidden" value="delete">
              <input name="id" type="hidden" value="%d">
              <button type="submit" class="btn-sm btn-danger">Delete</button>
            </form>
          </div>
        </li>
`, doneClass, t.ID, map[bool]string{true: "✓", false: "○"}[t.Done], t.Title, t.ID)
		}
		fmt.Fprintln(w, `
      </ul>
`)
	}

	fmt.Fprint(w, `
    </div>
  </div>

  <footer>
    Built with Go
  </footer>
</body>
</html>
`)
}
