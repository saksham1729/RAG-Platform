package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	requestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "auth_requests_total",
			Help: "Total requests handled by the auth service, labeled by route and status code.",
		},
		[]string{"path", "status"},
	)

	requestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "auth_request_duration_seconds",
			Help:    "Request duration in seconds, labeled by route.",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"path"},
	)
)

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(status int) {
	r.status = status
	r.ResponseWriter.WriteHeader(status)
}

func metricsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: 200}
		next.ServeHTTP(rec, r)
		duration := time.Since(start)

		requestsTotal.WithLabelValues(r.URL.Path, strconv.Itoa(rec.status)).Inc()
		requestDuration.WithLabelValues(r.URL.Path).Observe(duration.Seconds())
	})
}

type loginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type loginResponse struct {
	Token string `json:"token"`
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	mux := http.NewServeMux()

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})

	mux.Handle("/metrics", promhttp.Handler())

	// STUB: real implementation issues a signed JWT after verifying
	// credentials against Postgres. We'll wire real auth + a Postgres
	// connection in Module 4 once we have a database running in-cluster.
	mux.HandleFunc("/login", func(w http.ResponseWriter, r *http.Request) {
		var req loginRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "invalid request body", http.StatusBadRequest)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(loginResponse{Token: "stub-jwt-for-" + req.Email})
	})

	port := getEnv("PORT", "8080")
	log.Printf("auth service listening on :%s", port)
	if err := http.ListenAndServe(":"+port, metricsMiddleware(mux)); err != nil {
		log.Fatal(err)
	}
}
