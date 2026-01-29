````md
# Distributed Network Traffic (NetFlow) Analyzer + DDoS Detection (Apache Spark)
A phased build plan + tech stack for a resume-grade distributed systems project.

---

## 0) Project Summary

### Goal
Build a distributed pipeline that ingests **NetFlow-like** network flow records at high volume, performs **near real-time** aggregations, and detects **DDoS-like** anomalies (spikes, fan-in/fan-out) using **Apache Spark**.

### What makes it resume-worthy
- Distributed ingestion + processing (partitioning, shuffles, scaling)
- Streaming + windowed analytics
- Data-skew mitigation (heavy hitters)
- Fault tolerance + checkpoints
- Measured performance (throughput/latency) + write-up

### Core output
1) Aggregated network metrics per window (top talkers, top destinations, bytes/pps, unique sources)
2) Alerts for suspicious patterns (SYN flood-ish burst, many-to-one, one-to-many scans, etc.)
3) A reproducible deployment (Docker Compose) + a strong README/design notes

---

## 1) Tech Stack

### Required
- **Apache Spark 3.x** (Structured Streaming)
- **Python (PySpark)** (or Scala if you prefer; plan assumes PySpark)
- **Docker + Docker Compose** (multi-service local cluster)
- **Kafka-compatible message broker** (choose one):
  - **Redpanda** (easy single-binary Kafka API) **OR**
  - **Apache Kafka** (classic)
- **Storage**:
  - **Parquet** files (bronze/silver/gold layout)
  - Optional: **Delta Lake** (if you want upserts/time travel)

### Recommended (for polish)
- **Streamlit** or **Grafana**
  - Streamlit for quick dashboard from Parquet/Delta
  - Grafana if you push metrics to Prometheus/Loki (optional)
- **pytest** for unit tests
- **black/ruff** for formatting/linting

### Optional “Big-company vibes”
- **OpenTelemetry** tracing for the producer/consumer (lightweight)
- **Prometheus** metrics for pipeline health (processing lag, throughput)

---

## 2) Data Model

### NetFlow-like record (JSON)
Each event represents a flow summary (not raw packets):

```json
{
  "ts": "2026-01-29T12:34:56.123Z",
  "router_id": "rtr-03",
  "src_ip": "10.10.1.25",
  "dst_ip": "172.16.4.9",
  "src_port": 52314,
  "dst_port": 443,
  "proto": "TCP",
  "bytes": 8421,
  "packets": 12,
  "tcp_flags": "S", 
  "sampling_rate": 1
}
````

### Partitioning keys (important for distributed performance)

* Kafka key: `src_ip` OR `dst_ip` (depending on detection)
* Spark partition strategy: by `window_start` + `dst_ip` (for fan-in/DDOS) and/or by `src_ip` (for scans)

---

## 3) Repository Structure (suggested)

```
netflow-ddos-spark/
  README.md
  docs/
    design.md
    experiments.md
    architecture.png (optional)
  docker/
    docker-compose.yml
    spark/
      Dockerfile
    producer/
      Dockerfile
  producer/
    src/
      generate_flows.py
      scenarios.py
      config.py
  spark/
    src/
      streaming_job.py
      schema.py
      transforms.py
      detection.py
      sinks.py
    tests/
      test_detection.py
      test_transforms.py
  dashboard/
    app.py  (Streamlit)
  data/
    bronze/
    silver/
    gold/
    checkpoints/
```

---

## 4) Project Phases

## Phase 1 — MVP Foundations (Local End-to-End)

**Target outcome:** a working pipeline from generator → broker → Spark → Parquet.

### Tasks

1. **Flow generator**

   * Create a Python producer that emits baseline (normal) flows
   * Parameters:

     * events/sec
     * number of routers
     * number of hosts
     * distribution of dst ports (80/443 common)
   * Output to Kafka/Redpanda topic: `netflow.raw`

2. **Spark Structured Streaming consumer**

   * Read from Kafka topic
   * Parse JSON into a typed Spark schema
   * Add derived fields:

     * `event_time` from `ts`
     * `minute_bucket` or `window` later
     * `src_subnet` (e.g., /24)
     * `dst_subnet`

3. **Write Bronze**

   * Write raw parsed events to `data/bronze` as Parquet
   * Enable checkpointing to `data/checkpoints/bronze`

### Acceptance criteria

* You can run `docker-compose up` and see:

  * producer pushing events
  * Spark job running continuously
  * Parquet files appearing in `data/bronze`

### Notes (resume value)

* In README, explain:

  * why structured streaming
  * event time vs processing time
  * what checkpointing gives you (fault recovery)

---

## Phase 2 — Core Analytics (Windowed Aggregations)

**Target outcome:** compute network metrics per time window at scale.

### Metrics to compute (Gold tables)

Use tumbling windows (e.g., 1m) and optionally sliding (e.g., 5m sliding every 1m).

1. **Top talkers (by src_ip)**

   * `sum(bytes)`, `sum(packets)`, `count(flows)` per window

2. **Top destinations (by dst_ip)**

   * same aggregations, plus:
   * `approx_count_distinct(src_ip)` (unique sources per destination)

3. **Router-level summary**

   * per router/window:

     * total bytes/packets
     * top dst ports

### Data layout

* `silver`: cleaned + enriched flows
* `gold`: aggregations
* Partition by:

  * `date` and `window_start` (or `hour`) to speed queries

### Performance considerations (document these)

* Windowed groupBy triggers shuffles: call them out
* Cache where helpful (but avoid over-caching)
* Use `approx_count_distinct` where exact cardinality is expensive

### Acceptance criteria

* Gold outputs update continuously
* You can query and see “top talkers/destinations” per minute

---

## Phase 3 — Detection v1 (Rule-Based DDoS + Scan Signals)

**Target outcome:** generate alerts with simple, explainable logic (best for interviews).

### Detection signals (start with 3)

1. **Many-to-one burst (victim under attack)**

   * For each `dst_ip` in a window:

     * `unique_sources > S_threshold`
     * AND `packets_per_second > P_threshold` OR `bytes > B_threshold`

2. **One-to-many scan (source scanning many destinations)**

   * For each `src_ip`:

     * `unique_destinations > D_threshold`
     * AND many distinct ports (optional)

3. **SYN burst heuristic (optional)**

   * If you simulate TCP flags:

     * high ratio of SYN-only flags to completed flows

### Output (Alerts table)

Create an `alerts` sink with fields:

* `window_start`, `window_end`
* `alert_type` (FAN_IN_DDOS, FAN_OUT_SCAN, SYN_BURST)
* `entity` (dst_ip or src_ip)
* `score` (simple severity)
* `evidence` (counts/metrics)

### Acceptance criteria

* When you enable an “attack scenario” in the generator, alerts appear within 1–2 windows.

---

## Phase 4 — Attack Scenarios + Data Skew Handling (Realistic Stress)

**Target outcome:** the system remains stable under heavy hitters and shows engineering maturity.

### Add realistic scenarios to generator

1. **Baseline traffic** (normal diurnal patterns)
2. **DDoS fan-in** (many sources → one destination)
3. **Scan fan-out** (one source → many destinations)
4. **Flash crowd** (legitimate spike: many sources to popular endpoint)

   * helps reduce false positives

### Data skew mitigation (important!)

DDoS creates **hot keys** (one dst_ip). Add one or more:

* **Salting hot keys**:

  * For hot `dst_ip`, append random salt during aggregation, then re-aggregate
* **Two-stage aggregation**:

  * partial aggregation by (dst_ip, salt, window) then final by (dst_ip, window)
* Document why skew happens and what your approach is

### Acceptance criteria

* Under DDoS scenario, Spark job doesn’t collapse from a single hot partition
* You can show throughput improvement after skew mitigation

---

## Phase 5 — Reliability + Exactly-Once-ish Behavior

**Target outcome:** demonstrate fault tolerance and correctness under restarts.

### Tasks

* Ensure Spark streaming checkpointing is configured for all sinks
* Use deterministic output paths and idempotent writes where possible
* Test restarts:

  * kill Spark driver → restart → pipeline resumes
  * kill broker briefly → recover
* Track processing lag (Kafka offsets vs processed)

### Acceptance criteria

* After restart, pipeline continues without “starting over”
* No obvious duplicate alert explosion (some duplicates can be discussed honestly; show mitigations)

---

## Phase 6 — Evaluation & Experiments (This is what upgrades the resume)

**Target outcome:** produce a short “experiments.md” with results.

### Experiments to run

1. **Scale workers**

   * 1 vs 2 vs 4 Spark workers
   * measure max events/sec while keeping stable lag

2. **Window sizes**

   * 10s, 30s, 60s windows
   * effect on detection speed and compute load

3. **Skew test**

   * heavy hitter destination on/off
   * compare runtime/shuffle/processing lag

### Metrics to report

* Throughput (events/sec ingested and processed)
* End-to-end latency (event time to alert time)
* Processing lag (Kafka offsets or micro-batch delay)
* Costly operations (shuffle stages, groupBy)

### Acceptance criteria

* A clear chart/table in docs showing scaling behavior + bottlenecks
* A short paragraph explaining trade-offs and what you’d do next in production

---

## Phase 7 — Dashboard + Demo Polish

**Target outcome:** something you can show in a 60–90 second screen recording.

### Minimal dashboard pages (Streamlit)

* Live “Top Destinations” table (last N windows)
* Alert feed with severity + evidence
* Toggle scenario + show response (if you add control plane)

### Demo script

1. Start pipeline (normal traffic)
2. Turn on DDoS scenario
3. Show spike in unique_sources + packets/sec
4. Show alert generated
5. Turn off attack → system recovers

### Acceptance criteria

* A clean demo video/GIF
* README includes “Demo steps” and screenshots

---

## 5) Implementation Details (Guidelines)

### Spark streaming choices

* Use event-time windows with watermarks:

  * `withWatermark("event_time", "2 minutes")`
* Prefer incremental sinks (append mode) when possible
* Keep schemas explicit (avoid inference)

### Topics / sinks

* Kafka topic: `netflow.raw`
* Bronze sink: `data/bronze/netflow/`
* Silver sink: `data/silver/netflow_enriched/`
* Gold sinks:

  * `data/gold/top_talkers/`
  * `data/gold/top_destinations/`
  * `data/gold/router_summary/`
  * `data/gold/alerts/`

### Security note (for README)

This is a **simulation** and uses synthetic data. The focus is detection logic + distributed analytics, not operational offensive behavior.

---

## 6) Milestones Checklist (Quick)

* [ ] Phase 1: Producer → Kafka → Spark → Bronze Parquet
* [ ] Phase 2: Windowed aggregations to Gold
* [ ] Phase 3: Alerts table with 2–3 detectors
* [ ] Phase 4: Attack scenarios + skew mitigation
* [ ] Phase 5: Restart/recovery tests + checkpointing
* [ ] Phase 6: Experiments.md with scaling results
* [ ] Phase 7: Dashboard + demo recording

---

## 7) Resume + README Wording (templates)

### Resume bullet templates

* Built a distributed NetFlow-style analytics pipeline using Apache Spark Structured Streaming to process high-volume network telemetry in near real time
* Implemented windowed aggregations and DDoS/scanning detection with fault-tolerant checkpointing and scalable Parquet sinks
* Mitigated hot-key data skew during fan-in attacks using two-stage aggregation (key salting), improving pipeline stability under adversarial traffic patterns
* Benchmarked scaling across cluster sizes and event rates; analyzed shuffle bottlenecks and end-to-end alert latency

### README sections you should include

* System architecture diagram
* Data schema
* Detection logic (with thresholds)
* How to run (docker-compose)
* Experiments + findings
* Limitations + next steps

---

## 8) Stretch Goals (Pick 1–2 max)

* Add **Bloom filter / count-min sketch** for heavy hitter tracking
* Store alerts in a small DB and expose a REST API
* Add **false-positive handling**: flash-crowd suppression via baseline learning
* Add tracing/metrics (OpenTelemetry/Prometheus) for pipeline health

---

## 9) Next Steps (When you start later)

1. Implement Phase 1 exactly (end-to-end)
2. Get Phase 2 metrics working
3. Add one attack scenario + one detector (Phase 3)
4. Only then optimize and add skew handling

---

End of plan.

```
::contentReference[oaicite:0]{index=0}
```
