package metrics

import (
	"log"
	"sync/atomic"
	"time"
)

// Counter tracks production metrics
type Counter struct {
	messagesSent uint64
	bytesSent    uint64
	errors       uint64
	startTime    time.Time
}

// NewCounter creates a new metrics counter
func NewCounter() *Counter {
	return &Counter{
		startTime: time.Now(),
	}
}

// IncrementMessages atomically increments the message counter
func (c *Counter) IncrementMessages(count uint64) {
	atomic.AddUint64(&c.messagesSent, count)
}

// IncrementBytes atomically increments the bytes counter
func (c *Counter) IncrementBytes(bytes uint64) {
	atomic.AddUint64(&c.bytesSent, bytes)
}

// IncrementErrors atomically increments the error counter
func (c *Counter) IncrementErrors() {
	atomic.AddUint64(&c.errors, 1)
}

// GetStats returns current statistics
func (c *Counter) GetStats() (messages, bytes, errors uint64, duration time.Duration) {
	return atomic.LoadUint64(&c.messagesSent),
		atomic.LoadUint64(&c.bytesSent),
		atomic.LoadUint64(&c.errors),
		time.Since(c.startTime)
}

// StartReporter starts a goroutine that logs metrics periodically
func (c *Counter) StartReporter(interval time.Duration) {
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		var lastMessages uint64

		for range ticker.C {
			messages, bytes, errors, duration := c.GetStats()
			rate := float64(messages-lastMessages) / interval.Seconds()
			lastMessages = messages

			log.Printf("[METRICS] Total: %d msgs, %.2f MB | Rate: %.0f msg/sec | Errors: %d | Uptime: %s",
				messages,
				float64(bytes)/(1024*1024),
				rate,
				errors,
				duration.Round(time.Second),
			)
		}
	}()
}
