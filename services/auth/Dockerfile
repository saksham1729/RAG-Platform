# ---- Build stage ----
# Full Go toolchain lives only here; this layer never ships to production.
FROM golang:1.22-alpine AS builder

WORKDIR /src

# Copy dependency manifests first and download deps BEFORE copying source.
# Docker caches layers by content hash: as long as go.mod/go.sum don't change,
# this layer is reused on every rebuild, so `docker build` after a code-only
# change skips re-downloading dependencies entirely.
COPY go.mod ./
RUN go mod download

COPY . .

# CGO_ENABLED=0 produces a fully static binary (no libc dependency),
# which is what lets us run it on the minimal "scratch" base below.
RUN CGO_ENABLED=0 GOOS=linux go build -o /auth .

# ---- Runtime stage ----
# scratch = a literally empty base image. No shell, no package manager,
# no OS at all — just our one static binary. This is the smallest and
# most secure runtime image possible: nothing exists in it for an
# attacker to exploit even if they get code execution.
FROM scratch

COPY --from=builder /auth /auth

EXPOSE 8080

ENTRYPOINT ["/auth"]
