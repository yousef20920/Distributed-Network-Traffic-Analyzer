package kafka

import (
	"context"
	"encoding/json"
	"log"
	"time"

	"github.com/segmentio/kafka-go"
)

// Producer wraps the Kafka writer with additional functionality
type Producer struct {
	writer *kafka.Writer
	topic  string
}

// NewProducer creates a new Kafka producer
func NewProducer(brokers, topic string) *Producer {
	writer := &kafka.Writer{
		Addr:         kafka.TCP(brokers),
		Topic:        topic,
		Balancer:     &kafka.LeastBytes{},
		BatchSize:    100,
		BatchTimeout: 10 * time.Millisecond,
		RequiredAcks: kafka.RequireOne,
	}

	return &Producer{
		writer: writer,
		topic:  topic,
	}
}

// Send serializes and sends a message to Kafka
func (p *Producer) Send(ctx context.Context, value interface{}) error {
	data, err := json.Marshal(value)
	if err != nil {
		return err
	}

	return p.writer.WriteMessages(ctx, kafka.Message{
		Value: data,
	})
}

// SendBatch sends multiple messages in a batch
func (p *Producer) SendBatch(ctx context.Context, values []interface{}) error {
	messages := make([]kafka.Message, len(values))
	for i, v := range values {
		data, err := json.Marshal(v)
		if err != nil {
			return err
		}
		messages[i] = kafka.Message{Value: data}
	}

	return p.writer.WriteMessages(ctx, messages...)
}

// Close closes the Kafka writer
func (p *Producer) Close() error {
	if err := p.writer.Close(); err != nil {
		log.Printf("Error closing Kafka writer: %v", err)
		return err
	}
	return nil
}
