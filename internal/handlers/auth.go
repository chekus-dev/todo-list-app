package handlers

import (
	"fmt"
	"golang.org/x/crypto/bcrypt"
	"net/http"
)

func pageTop(title string) string {
	return fmt.Sprintf(`
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>%s • Todo App</title>
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
`, title)
}

func pageBottom() string {
	return `
    </div>
  </div>

  <footer>
    Built with Go
  </footer>
</body>
</html>
`
}

func (h *Handler) Login(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprint(w, pageTop("Login"))
		fmt.Fprintln(w, `
      <h1>Login</h1>
      <form method="post" action="/login">
        <div>
          <label for="email">Email</label>
          <input id="email" name="email" type="email" placeholder="you@example.com" required>
        </div>
        <div style="margin-top:0.75rem">
          <label for="password">Password</label>
          <input id="password" name="password" type="password" placeholder="Your password" required>
        </div>
        <div style="margin-top:1rem">
          <button type="submit">Login</button>
        </div>
      </form>
      <p style="margin-top:1rem">
        Don’t have an account? <a href="/register">Register</a>
      </p>
`)
		fmt.Fprint(w, pageBottom())
		return
	}

	email := r.FormValue("email")
	password := r.FormValue("password")

	u, err := h.userStore.GetByEmail(email)
	if err != nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprint(w, pageTop("Login"))
		fmt.Fprintln(w, `
      <h1>Login</h1>
      <p class="error">Invalid email or password.</p>
      <form method="post" action="/login">
        <div>
          <label for="email">Email</label>
          <input id="email" name="email" type="email" placeholder="you@example.com" required>
        </div>
        <div style="margin-top:0.75rem">
          <label for="password">Password</label>
          <input id="password" name="password" type="password" placeholder="Your password" required>
        </div>
        <div style="margin-top:1rem">
          <button type="submit">Login</button>
        </div>
      </form>
      <p style="margin-top:1rem">
        Don’t have an account? <a href="/register">Register</a>
      </p>
`)
		fmt.Fprint(w, pageBottom())
		return
	}

	if err := bcrypt.CompareHashAndPassword(u.Password, []byte(password)); err != nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprint(w, pageTop("Login"))
		fmt.Fprintln(w, `
      <h1>Login</h1>
      <p class="error">Invalid email or password.</p>
      <form method="post" action="/login">
        <div>
          <label for="email">Email</label>
          <input id="email" name="email" type="email" placeholder="you@example.com" required>
        </div>
        <div style="margin-top:0.75rem">
          <label for="password">Password</label>
          <input id="password" name="password" type="password" placeholder="Your password" required>
        </div>
        <div style="margin-top:1rem">
          <button type="submit">Login</button>
        </div>
      </form>
      <p style="margin-top:1rem">
        Don’t have an account? <a href="/register">Register</a>
      </p>
`)
		fmt.Fprint(w, pageBottom())
		return
	}

	h.session.Set(w, u.ID)
	http.Redirect(w, r, "/todos", http.StatusSeeOther)
}

func (h *Handler) Logout(w http.ResponseWriter, r *http.Request) {
	h.session.Clear(w)
	http.Redirect(w, r, "/", http.StatusSeeOther)
}

func (h *Handler) Register(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprint(w, pageTop("Register"))
		fmt.Fprintln(w, `
      <h1>Create your account</h1>
      <form method="post" action="/register">
        <div>
          <label for="email">Email</label>
          <input id="email" name="email" type="email" placeholder="you@example.com" required>
        </div>
        <div style="margin-top:0.75rem">
          <label for="password">Password</label>
          <input id="password" name="password" type="password" placeholder="Choose a password" required>
        </div>
        <div style="margin-top:1rem">
          <button type="submit">Register</button>
        </div>
      </form>
      <p style="margin-top:1rem">
        Already have an account? <a href="/login">Login</a>
      </p>
`)
		fmt.Fprint(w, pageBottom())
		return
	}

	email := r.FormValue("email")
	password := r.FormValue("password")

	hashed, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	u, err := h.userStore.Create(email, hashed)
	if err != nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprint(w, pageTop("Register"))
		fmt.Fprintln(w, `
      <h1>Create your account</h1>
      <p class="error">Failed to create user. The email may already be in use.</p>
      <form method="post" action="/register">
        <div>
          <label for="email">Email</label>
          <input id="email" name="email" type="email" placeholder="you@example.com" required>
        </div>
        <div style="margin-top:0.75rem">
          <label for="password">Password</label>
          <input id="password" name="password" type="password" placeholder="Choose a password" required>
        </div>
        <div style="margin-top:1rem">
          <button type="submit">Register</button>
        </div>
      </form>
      <p style="margin-top:1rem">
        Already have an account? <a href="/login">Login</a>
      </p>
`)
		fmt.Fprint(w, pageBottom())
		return
	}

	h.session.Set(w, u.ID)
	http.Redirect(w, r, "/todos", http.StatusSeeOther)
}
