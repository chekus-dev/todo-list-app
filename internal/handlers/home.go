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

	fmt.Println("Rendering home.html")
	err := h.templates.ExecuteTemplate(w, "home.html", nil)
	if err != nil {
		fmt.Println("Template error:", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}