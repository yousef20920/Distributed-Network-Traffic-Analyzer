FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum* ./
RUN go mod download

# Copy source
COPY . .

# Build
RUN CGO_ENABLED=0 GOOS=linux go build -o /producer ./cmd/producer

# Runtime image
FROM alpine:3.19

RUN apk --no-cache add ca-certificates

COPY --from=builder /producer /producer

ENTRYPOINT ["/producer"]
