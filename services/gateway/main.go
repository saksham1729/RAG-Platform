package main

import (
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// These three metrics together implement the RED method (Rate, Errors,
// Duration) for this service. Prometheus scrapes them from /metrics on
// whatever interval we configure later — nothing pushes these anywhere;
// they just sit here as current counters/histograms until scraped.
var (
	requestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "gateway_requests_total",
			Help: "Total number of requests handled by the gateway, labeled by route and status code.",
		},
		[]string{"path", "status"},
	)

	requestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "gateway_request_duration_seconds",
			Help:    "Request duration in seconds, labeled by route.",
			Buckets: prometheus.DefBuckets, // sensible default latency buckets (5ms to 10s)
		},
		[]string{"path"},
	)
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

// loggingMiddleware wraps a handler, logs each request, AND records the
// same information as Prometheus metrics. Logs and metrics are generated
// from the same event here deliberately — they're different VIEWS of the
// same request, not different data sources.
func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: 200}
		next.ServeHTTP(rec, r)
		duration := time.Since(start)

		log.Printf(`method=%s path=%s status=%d duration_ms=%d`,
			r.Method, r.URL.Path, rec.status, duration.Milliseconds())

		requestsTotal.WithLabelValues(r.URL.Path, strconv.Itoa(rec.status)).Inc()
		requestDuration.WithLabelValues(r.URL.Path).Observe(duration.Seconds())
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

	// promhttp.Handler() serves the current state of every registered
	// metric in Prometheus's text exposition format — this is literally
	// what Prometheus's scraper parses on its scrape interval.
	mux.Handle("/metrics", promhttp.Handler())

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
