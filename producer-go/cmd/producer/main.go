package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/distributed-netflow-analyzer/producer-go/internal/config"
	"github.com/distributed-netflow-analyzer/producer-go/internal/kafka"
	"github.com/distributed-netflow-analyzer/producer-go/internal/metrics"
	"github.com/distributed-netflow-analyzer/producer-go/internal/netflow"
)

func main() {
	cfg := config.Load()

	log.Printf("Starting NetFlow Producer")
	log.Printf("  Router ID:    %s", cfg.RouterID)
	log.Printf("  Scenario:     %s", cfg.Scenario)
	log.Printf("  Kafka:        %s", cfg.KafkaBrokers)
	log.Printf("  Topic:        %s", cfg.Topic)
	log.Printf("  Target Rate:  %d events/sec", cfg.EventsPerSec)

	// Initialize components
	producer := kafka.NewProducer(cfg.KafkaBrokers, cfg.Topic)
	defer producer.Close()

	generator := netflow.NewGenerator(cfg.RouterID, cfg.Scenario)
	counter := metrics.NewCounter()

	// Start metrics reporter
	counter.StartReporter(5 * time.Second)

	// Setup graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigChan
		log.Println("Shutting down...")
		cancel()
	}()

	// Calculate interval between events
	interval := time.Second / time.Duration(cfg.EventsPerSec)
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	// Batch settings
	batchSize := 100
	batch := make([]interface{}, 0, batchSize)

	log.Println("Producing flows...")

	for {
		select {
		case <-ctx.Done():
			// Send remaining batch
			if len(batch) > 0 {
				if err := producer.SendBatch(ctx, batch); err != nil {
					log.Printf("Error sending final batch: %v", err)
				}
			}
			log.Println("Producer stopped")
			return

		case <-ticker.C:
			record := generator.Generate()
			batch = append(batch, record)

			if len(batch) >= batchSize {
				if err := producer.SendBatch(ctx, batch); err != nil {
					log.Printf("Error sending batch: %v", err)
					counter.IncrementErrors()
				} else {
					counter.IncrementMessages(uint64(len(batch)))
				}
				batch = batch[:0]
			}
		}
	}
}
