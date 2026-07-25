package main

import (
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"time"
)

// route maps a URL path prefix to a backend service.
// In Kubernetes, targetURL will be a Service DNS name like
// "http://chat-service.default.svc.cluster.local:8000" — not localhost.
// We read these from env vars so the same binary works locally and in-cluster.
type route struct {
	prefix    string
	targetURL string
}

func mustParseURL(raw string) *url.URL {
	u, err := url.Parse(raw)
	if err != nil {
		log.Fatalf("invalid backend URL %q: %v", raw, err)
	}
	return u
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

// loggingMiddleware wraps a handler and logs method, path, status, and latency.
// This structured line is what Module 10 (Loki/EFK) will scrape and index.
func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: 200}
		next.ServeHTTP(rec, r)
		log.Printf(`method=%s path=%s status=%d duration_ms=%d`,
			r.Method, r.URL.Path, rec.status, time.Since(start).Milliseconds())
	})
}

// statusRecorder captures the status code written by downstream handlers,
// since http.ResponseWriter doesn't expose it after the fact.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(status int) {
	r.status = status
	r.ResponseWriter.WriteHeader(status)
}

func main() {
	mux := http.NewServeMux()

	// Health check — Kubernetes liveness/readiness probes hit this.
	// It must NOT depend on backend services being up; it only proves
	// this process is alive and able to serve HTTP.
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})

	routes := []route{
		{prefix: "/api/auth", targetURL: getEnv("AUTH_SERVICE_URL", "http://localhost:8001")},
		{prefix: "/api/chat", targetURL: getEnv("CHAT_SERVICE_URL", "http://localhost:8002")},
		{prefix: "/api/ingestion", targetURL: getEnv("INGESTION_SERVICE_URL", "http://localhost:8003")},
		{prefix: "/api/retrieval", targetURL: getEnv("RETRIEVAL_SERVICE_URL", "http://localhost:8004")},
	}

	for _, rt := range routes {
		target := mustParseURL(rt.targetURL)
		proxy := httputil.NewSingleHostReverseProxy(target)
		mux.Handle(rt.prefix+"/", http.StripPrefix(rt.prefix, proxy))
		log.Printf("routing %s/* -> %s", rt.prefix, rt.targetURL)
	}

	handler := loggingMiddleware(mux)

	port := getEnv("PORT", "8080")
	log.Printf("gateway listening on :%s", port)
	if err := http.ListenAndServe(":"+port, handler); err != nil {
		log.Fatal(err)
	}
}
