package handlers

import (
	"golang.org/x/crypto/bcrypt"
	"net/http"
)

func (h *Handler) Login(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		_ = h.templates.ExecuteTemplate(w, "login.html", nil)
		return
	}

	email := r.FormValue("email")
	password := r.FormValue("password")

	u, err := h.userStore.GetByEmail(email)
	if err != nil {
		_ = h.templates.ExecuteTemplate(w, "login.html", map[string]string{
			"Error": "Invalid email or password",
		})
		return
	}

	if err := bcrypt.CompareHashAndPassword(u.Password, []byte(password)); err != nil {
		_ = h.templates.ExecuteTemplate(w, "login.html", map[string]string{
			"Error": "Invalid email or password",
		})
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
		_ = h.templates.ExecuteTemplate(w, "register.html", nil)
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
		_ = h.templates.ExecuteTemplate(w, "register.html", map[string]string{
			"Error": "Failed to create user (email may exist)",
		})
		return
	}

	h.session.Set(w, u.ID)
	http.Redirect(w, r, "/todos", http.StatusSeeOther)
}
