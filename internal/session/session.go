package session

import (
	"encoding/base64"
	"net/http"
	"strconv"

	"time"
)

type CookieSessionStore struct {
	secret []byte
	maxAge time.Duration
}

func NewCookieSessionStore(secret []byte, maxAge time.Duration) *CookieSessionStore {
	return &CookieSessionStore{secret: secret, maxAge: maxAge}
}

func encodeUser(id int64, secret []byte) string {
	data := []byte(strconv.FormatInt(id, 10))
	for i := range data {
		data[i] ^= secret[i%len(secret)]
	}
	return base64.StdEncoding.EncodeToString(data)
}

func decodeUser(token string, secret []byte) (int64, error) {
	data, err := base64.StdEncoding.DecodeString(token)
	if err != nil {
		return 0, err
	}
	for i := range data {
		data[i] ^= secret[i%len(secret)]
	}
	id, err := strconv.ParseInt(string(data), 10, 64)
	if err != nil {
		return 0, err
	}
	return id, nil
}

func (s *CookieSessionStore) Set(w http.ResponseWriter, userID int64) {
	token := encodeUser(userID, s.secret)
	c := &http.Cookie{
		Name:     "session",
		Value:    token,
		Path:     "/",
		HttpOnly: true,
		MaxAge:   int(s.maxAge.Seconds()),
	}
	http.SetCookie(w, c)
}

func (s *CookieSessionStore) Get(r *http.Request) (int64, bool) {
	c, err := r.Cookie("session")
	if err != nil {
		return 0, false
	}
	id, err := decodeUser(c.Value, s.secret)
	if err != nil {
		return 0, false
	}
	return id, true
}

func (s *CookieSessionStore) Clear(w http.ResponseWriter) {
	c := &http.Cookie{
		Name:     "session",
		Value:    "",
		Path:     "/",
		HttpOnly: true,
		MaxAge:   -1,
	}
	http.SetCookie(w, c)
}
