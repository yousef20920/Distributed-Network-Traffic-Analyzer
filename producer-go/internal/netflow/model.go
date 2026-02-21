package netflow

import (
	"time"
)

// FlowRecord represents a NetFlow v5-style record
type FlowRecord struct {
	Timestamp    time.Time `json:"ts"`
	RouterID     string    `json:"router_id"`
	SrcIP        string    `json:"src_ip"`
	DstIP        string    `json:"dst_ip"`
	SrcPort      int       `json:"src_port"`
	DstPort      int       `json:"dst_port"`
	Protocol     string    `json:"proto"`
	Bytes        int64     `json:"bytes"`
	Packets      int       `json:"packets"`
	TCPFlags     string    `json:"tcp_flags"`
	SamplingRate int       `json:"sampling_rate"`
}
