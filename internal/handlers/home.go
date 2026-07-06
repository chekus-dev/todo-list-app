package handlers

import (
	"fmt"
	"net/http"
)

func (h *Handler) Home(w http.ResponseWriter, r *http.Request) {
	_, ok := h.session.Get(r)
	if ok {
		http.Redirect(w, r, "/todos", http.StatusSeeOther)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprintln(w, `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Home • Todo App</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header>
    <div class="inner">
      <a class="brand" href="/">Todo App</a>
      <nav>
        <a href="/login">Login</a>
        <a href="/register">Register</a>
      </nav>
    </div>
  </header>

  <div class="container">
    <div class="card">
      <h1>Welcome</h1>
      <p>Manage your tasks with a simple, fast todo app.</p>
      <p>
        <a href="/login">Login</a> or <a href="/register">create an account</a> to get started.
      </p>
    </div>
  </div>

  <footer>
    Built with Go
  </footer>
</body>
</html>
`)
}
