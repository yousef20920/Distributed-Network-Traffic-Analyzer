package netflow

import (
	"fmt"
	"math/rand"
	"time"
)

// Generator creates FlowRecords based on different scenarios
type Generator struct {
	RouterID string
	Scenario string
	rng      *rand.Rand
}

// NewGenerator creates a new flow generator
func NewGenerator(routerID, scenario string) *Generator {
	return &Generator{
		RouterID: routerID,
		Scenario: scenario,
		rng:      rand.New(rand.NewSource(time.Now().UnixNano())),
	}
}

// Generate creates a FlowRecord based on the current scenario
func (g *Generator) Generate() FlowRecord {
	switch g.Scenario {
	case "ddos_fan_in":
		return g.generateDDoS()
	case "scan_fan_out":
		return g.generateScan()
	case "flash_crowd":
		return g.generateFlashCrowd()
	default:
		return g.generateBaseline()
	}
}

// generateBaseline creates normal traffic patterns
func (g *Generator) generateBaseline() FlowRecord {
	protocols := []string{"TCP", "UDP", "ICMP"}
	tcpFlags := []string{"", "SYN", "SYN-ACK", "ACK", "FIN", "RST"}
	commonPorts := []int{80, 443, 22, 53, 8080, 3306, 5432, 6379}

	proto := protocols[g.rng.Intn(len(protocols))]
	flags := ""
	if proto == "TCP" {
		flags = tcpFlags[g.rng.Intn(len(tcpFlags))]
	}

	return FlowRecord{
		Timestamp:    time.Now(),
		RouterID:     g.RouterID,
		SrcIP:        g.randomIP(),
		DstIP:        g.randomIP(),
		SrcPort:      g.rng.Intn(65535-1024) + 1024,
		DstPort:      commonPorts[g.rng.Intn(len(commonPorts))],
		Protocol:     proto,
		Bytes:        int64(g.rng.Intn(10000) + 100),
		Packets:      g.rng.Intn(50) + 1,
		TCPFlags:     flags,
		SamplingRate: 1,
	}
}

// generateDDoS creates fan-in attack traffic (many sources -> one target)
func (g *Generator) generateDDoS() FlowRecord {
	targetIP := "172.16.4.100" // Fixed target for DDoS
	botnetSize := 1000

	return FlowRecord{
		Timestamp:    time.Now(),
		RouterID:     g.RouterID,
		SrcIP:        g.randomBotnetIP(botnetSize),
		DstIP:        targetIP,
		SrcPort:      g.rng.Intn(65535-1024) + 1024,
		DstPort:      80,
		Protocol:     "TCP",
		Bytes:        int64(g.rng.Intn(50000) + 10000),
		Packets:      g.rng.Intn(100) + 50,
		TCPFlags:     "SYN",
		SamplingRate: 1,
	}
}

// generateScan creates fan-out scan traffic (one source -> many targets)
func (g *Generator) generateScan() FlowRecord {
	scannerIP := "10.0.0.99" // Fixed scanner IP
	scanPorts := []int{21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3389, 8080}

	return FlowRecord{
		Timestamp:    time.Now(),
		RouterID:     g.RouterID,
		SrcIP:        scannerIP,
		DstIP:        g.randomIP(),
		SrcPort:      g.rng.Intn(65535-1024) + 1024,
		DstPort:      scanPorts[g.rng.Intn(len(scanPorts))],
		Protocol:     "TCP",
		Bytes:        int64(g.rng.Intn(100) + 40),
		Packets:      1,
		TCPFlags:     "SYN",
		SamplingRate: 1,
	}
}

// generateFlashCrowd creates legitimate high-traffic to popular destinations
func (g *Generator) generateFlashCrowd() FlowRecord {
	popularSites := []string{"172.16.1.10", "172.16.1.20", "172.16.1.30"}
	target := popularSites[g.rng.Intn(len(popularSites))]

	return FlowRecord{
		Timestamp:    time.Now(),
		RouterID:     g.RouterID,
		SrcIP:        g.randomIP(),
		DstIP:        target,
		SrcPort:      g.rng.Intn(65535-1024) + 1024,
		DstPort:      443,
		Protocol:     "TCP",
		Bytes:        int64(g.rng.Intn(5000) + 500),
		Packets:      g.rng.Intn(20) + 5,
		TCPFlags:     "ACK",
		SamplingRate: 1,
	}
}

// randomIP generates a random private IP address
func (g *Generator) randomIP() string {
	// Mix of 10.x.x.x and 192.168.x.x
	if g.rng.Float32() < 0.7 {
		return fmt.Sprintf("10.%d.%d.%d", g.rng.Intn(256), g.rng.Intn(256), g.rng.Intn(254)+1)
	}
	return fmt.Sprintf("192.168.%d.%d", g.rng.Intn(256), g.rng.Intn(254)+1)
}

// randomBotnetIP generates an IP from a simulated botnet
func (g *Generator) randomBotnetIP(size int) string {
	botID := g.rng.Intn(size)
	return fmt.Sprintf("10.%d.%d.%d", (botID/65536)%256, (botID/256)%256, botID%256)
}
