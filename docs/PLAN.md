# 📋 Distributed NetFlow Analyzer — Execution Plan

> A phased, detailed implementation plan for building a resume-grade distributed systems project.

---

## 📅 Timeline Overview

| Phase | Focus | Duration | Status |
|-------|-------|----------|--------|
| 1 | Infrastructure + End-to-End MVP | Week 1 | ⬜ |
| 2 | Data Enrichment (Silver Layer) | Week 2 | ⬜ |
| 3 | Windowed Aggregations (Gold) | Week 2-3 | ⬜ |
| 4 | DDoS & Scan Detection | Week 3 | ⬜ |
| 5 | Attack Scenarios (Go Producer) | Week 4 | ⬜ |
| 6 | Data Skew Optimization | Week 4-5 | ⬜ |
| 7 | Reliability & Recovery | Week 5 | ⬜ |
| 8 | Experiments & Benchmarks | Week 6 | ⬜ |
| 9 | Dashboard & Demo | Week 6-7 | ⬜ |

---

## Phase 1 — Infrastructure + End-to-End MVP

**Goal:** Go producer → Kafka → Spark → Parquet (Bronze)

### Deliverables

- [ ] Docker Compose with all services
- [ ] Go producer generating baseline traffic
- [ ] PySpark job ingesting and writing Bronze Parquet

### Tasks

#### 1.1 Docker Compose Setup
```yaml
services:
  - redpanda (or kafka + zookeeper)
  - spark-master
  - spark-worker-1
  - spark-worker-2
  - producer-go (replicas: 3)
```

Create topic `netflow.raw` with 6-12 partitions.

#### 1.2 Go Producer (Baseline)

Implement in `producer-go/`:

```go
// internal/netflow/model.go
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
```

Configuration via environment:
- `KAFKA_BROKERS`
- `TOPIC`
- `EVENTS_PER_SEC`
- `ROUTER_ID`
- `SCENARIO` (baseline, ddos, scan)

#### 1.3 PySpark Streaming Job

```python
# streaming_job.py
df = spark.readStream \
    .format("kafka") \
    .option("subscribe", "netflow.raw") \
    .load()

parsed = df.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

parsed.writeStream \
    .format("parquet") \
    .option("path", "data/bronze/netflow/") \
    .option("checkpointLocation", "data/checkpoints/bronze/") \
    .start()
```

### Acceptance Criteria

- ✅ `docker-compose up` produces continuous Parquet in `bronze/`
- ✅ Spark job survives restarts via checkpointing
- ✅ Producer logs show ~1000 events/sec baseline

---

## Phase 2 — Enrichment (Silver Layer)

**Goal:** Cleaned, enriched dataset ready for analytics.

### Deliverables

- [ ] Enrichment transformations in Spark
- [ ] Silver Parquet output partitioned by date

### Enrichment Fields

| Field | Logic |
|-------|-------|
| `src_subnet_24` | First 3 octets of src_ip |
| `dst_subnet_24` | First 3 octets of dst_ip |
| `is_private_src` | RFC 1918 check |
| `is_private_dst` | RFC 1918 check |
| `dst_service` | Map port → service (80=HTTP, 443=HTTPS, 22=SSH, 53=DNS) |

### Output

```
data/silver/netflow_enriched/
├── date=2026-01-29/
│   └── part-*.parquet
```

### Acceptance Criteria

- ✅ Silver data updates continuously
- ✅ Schema documented in `docs/design.md`

---

## Phase 3 — Windowed Aggregations (Gold Metrics)

**Goal:** Real-time analytics tables.

### Deliverables

- [ ] Top Talkers (by src_ip)
- [ ] Top Destinations (by dst_ip)
- [ ] Router Summary

### Implementation

Use **1-minute tumbling windows** with watermarks:

```python
from pyspark.sql.functions import window

top_destinations = silver_df \
    .withWatermark("event_time", "2 minutes") \
    .groupBy(
        window("event_time", "1 minute"),
        "dst_ip"
    ) \
    .agg(
        sum("bytes").alias("total_bytes"),
        sum("packets").alias("total_packets"),
        approx_count_distinct("src_ip").alias("unique_sources")
    )
```

### Gold Tables

| Table | Group By | Metrics |
|-------|----------|---------|
| `top_talkers` | window, src_ip | bytes, packets, flow_count |
| `top_destinations` | window, dst_ip | bytes, packets, unique_sources |
| `router_summary` | window, router_id | bytes, packets, top_ports |

### Acceptance Criteria

- ✅ Gold outputs update every window
- ✅ Can query latest window for obvious "top" entities

---

## Phase 4 — DDoS & Scan Detection

**Goal:** Alert generation from explainable heuristics.

### Detection Rules

#### 1. Fan-In DDoS (Many → One)

```python
ddos_candidates = top_destinations.filter(
    (col("unique_sources") > 100) &
    ((col("total_packets") > 10000) | (col("total_bytes") > 10_000_000))
)
```

#### 2. Fan-Out Scan (One → Many)

```python
scan_candidates = top_talkers_extended.filter(
    (col("unique_destinations") > 50) &
    (col("distinct_ports") > 20)
)
```

#### 3. SYN Burst (Optional)

```python
syn_burst = window_flows.filter(
    col("syn_only_ratio") > 0.8
)
```

### Alerts Schema

```python
class Alert:
    window_start: timestamp
    window_end: timestamp
    alert_type: str  # FAN_IN_DDOS, FAN_OUT_SCAN, SYN_BURST
    entity: str      # dst_ip or src_ip
    severity_score: float
    unique_sources: int
    total_packets: int
    total_bytes: int
```

Output: `data/gold/alerts/`

### Acceptance Criteria

- ✅ Attack scenario triggers alerts within 1-2 windows
- ✅ Alerts include evidence for explainability

---

## Phase 5 — Attack Scenarios (Go Producer)

**Goal:** Controllable traffic patterns.

### Scenarios

| Scenario | Behavior | Use Case |
|----------|----------|----------|
| `baseline` | Normal traffic distribution | Default |
| `ddos_fan_in` | Many random src → one dst | Test DDoS detection |
| `scan_fan_out` | One src → many dst:ports | Test scan detection |
| `flash_crowd` | Many src → popular dst:443 | Test false positives |

### Configuration Knobs

```bash
SCENARIO=ddos_fan_in
EVENTS_PER_SEC=5000
ATTACK_INTENSITY=0.8
TARGET_IP=172.16.4.100
BOTNET_SIZE=1000
DURATION_SECONDS=300
```

### Implementation

```go
// internal/netflow/scenarios.go

func (g *Generator) GenerateDDoS(target string, botnetSize int) FlowRecord {
    return FlowRecord{
        SrcIP:   randomBotnetIP(botnetSize),
        DstIP:   target,
        DstPort: 80,
        Packets: rand.Intn(100) + 50,
        Bytes:   rand.Intn(50000) + 10000,
    }
}
```

### Acceptance Criteria

- ✅ Can run multiple producers with different scenarios
- ✅ System stable under 5000+ events/sec

---

## Phase 6 — Data Skew Optimization

**Goal:** Pipeline performs under hot-key attacks.

### The Problem

During fan-in DDoS, `dst_ip=target` becomes a **hot key** causing one partition to bottleneck.

### Solution: Two-Stage Aggregation

```python
# Stage 1: Add salt for hot keys
salted = df.withColumn(
    "salt", 
    (hash("src_ip") % 10)
)

partial_agg = salted.groupBy(
    window("event_time", "1 minute"),
    "dst_ip",
    "salt"
).agg(sum("bytes"), sum("packets"), collect_set("src_ip"))

# Stage 2: Combine salted partitions
final_agg = partial_agg.groupBy(
    "window",
    "dst_ip"
).agg(
    sum("sum(bytes)"),
    sum("sum(packets)"),
    size(flatten(collect_list("collect_set(src_ip)")))
)
```

### Acceptance Criteria

- ✅ DDoS scenario doesn't stall pipeline
- ✅ Before/after documented in `docs/experiments.md`

---

## Phase 7 — Reliability & Recovery

**Goal:** Demonstrate fault tolerance.

### Tests

| Test | Expected Behavior |
|------|-------------------|
| Kill Spark driver | Job resumes from checkpoint |
| Kill one worker | Job continues on remaining workers |
| Restart broker | Job recovers after reconnection |

### Configuration

- Separate checkpoint dirs per sink
- Deterministic output paths
- Discuss idempotency honestly in design doc

### Acceptance Criteria

- ✅ System resumes without manual cleanup
- ✅ No duplicate alerts explosion after restart

---

## Phase 8 — Experiments & Benchmarks

**Goal:** Strong experimental report for resume.

### Experiments

#### 8.1 Scale-Out Test
| Workers | Max Events/Sec | Latency (p99) |
|---------|----------------|---------------|
| 1 | ? | ? |
| 2 | ? | ? |
| 4 | ? | ? |

#### 8.2 Window Size Trade-offs
| Window | Detection Speed | CPU Cost |
|--------|-----------------|----------|
| 10s | Fast | High |
| 60s | Slower | Lower |

#### 8.3 Skew Impact
| Scenario | Processing Lag | Throughput |
|----------|----------------|------------|
| Baseline | ? | ? |
| DDoS (no salt) | ? | ? |
| DDoS (with salt) | ? | ? |

### Metrics to Collect

- Events/sec ingested (producer logs)
- Micro-batch duration (Spark UI)
- End-to-end latency (event_time → alert_time)
- Shuffle read/write sizes

### Acceptance Criteria

- ✅ `docs/experiments.md` has tables + graphs
- ✅ "Bottlenecks" section explaining limits

---

## Phase 9 — Dashboard & Demo

**Goal:** 60-90 second demo for recruiters.

### Streamlit Pages

1. **Live Metrics** — Top destinations, talkers (last N windows)
2. **Alerts Feed** — Sorted by severity, real-time updates
3. **Scenario Control** — Toggle attack modes
4. **System Health** — Pipeline lag, throughput

### Demo Flow

```
1. Start with baseline → no alerts
2. Enable ddos_fan_in → show spike → alert appears
3. Switch to scan_fan_out → scan alerts appear
4. Return to baseline → system recovers
```

### Acceptance Criteria

- ✅ Clean demo recording
- ✅ Screenshots in README

---

## 🎯 Stretch Goals (Pick 1-2)

- [ ] **Alert Service** — Go service consuming `netflow.alerts` topic, deduplicates, exposes REST/gRPC
- [ ] **Heavy Hitters** — Count-Min Sketch for approximate detection
- [ ] **Pipeline Metrics** — Prometheus exporters + Grafana dashboards
- [ ] **False Positive Suppression** — Rolling baseline to distinguish flash crowds from attacks

---

## 📝 Resume Bullets

Use these to describe the project:

> - Built a distributed NetFlow-style analytics pipeline using **Go producers** and **Apache Spark Structured Streaming** to process high-volume network telemetry in near real time
> - Implemented event-time windowed aggregations and **DDoS/scan detection** with fault-tolerant checkpointing and partitioned Parquet sinks  
> - Mitigated hot-key data skew during fan-in attacks using **two-stage aggregation (key salting)**, improving pipeline stability under adversarial traffic patterns
> - Benchmarked scaling across cluster sizes and event rates; analyzed shuffle bottlenecks and end-to-end alert latency using Spark streaming metrics

---

## ⏭️ Recommended Order

1. **Phase 1** — End-to-end working first (don't optimize early)
2. **Phase 3** — Add aggregations (learn Spark windows)
3. **Phase 4-5** — One scenario + one detector
4. **Phase 6-8** — Skew mitigation + experiments last
5. **Phase 9** — Dashboard for demo

---

*Last updated: January 2026*
