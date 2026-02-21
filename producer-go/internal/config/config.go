package config

import (
	"os"
	"strconv"
)

type Config struct {
	KafkaBrokers  string
	Topic         string
	EventsPerSec  int
	RouterID      string
	Scenario      string
}

func Load() *Config {
	return &Config{
		KafkaBrokers:  getEnv("KAFKA_BROKERS", "localhost:9092"),
		Topic:         getEnv("TOPIC", "netflow.raw"),
		EventsPerSec:  getEnvInt("EVENTS_PER_SEC", 1000),
		RouterID:      getEnv("ROUTER_ID", "router-1"),
		Scenario:      getEnv("SCENARIO", "baseline"),
	}
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	if value := os.Getenv(key); value != "" {
		if i, err := strconv.Atoi(value); err == nil {
			return i
		}
	}
	return fallback
}
