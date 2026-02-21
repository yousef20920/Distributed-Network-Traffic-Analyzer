# 🌐 Distributed NetFlow Analyzer

> **Real-time network traffic analytics & DDoS detection using Go, Apache Spark, and Kafka**

A distributed pipeline that ingests high-volume NetFlow-like records, performs near real-time analytics with Spark Structured Streaming, and detects DDoS attacks and network anomalies.

---

## ✨ Features

- **High-Throughput Ingestion** — Go producers with goroutine concurrency and backpressure handling
- **Real-Time Streaming** — Spark Structured Streaming with event-time windows and watermarks
- **DDoS Detection** — Fan-in attacks (many→one), port scans (one→many), SYN floods
- **Scalable Storage** — Bronze/Silver/Gold data lake architecture with Parquet
- **Fault Tolerant** — Checkpointing, recovery from failures, exactly-once semantics
- **Observable** — Live dashboard with Streamlit, optional Prometheus/Grafana metrics

---

## 🏗️ Architecture

```
┌─────────────────────┐      ┌─────────────────────┐
│   Go Flow Producers │─────▶│  Kafka / Redpanda   │
│   (Router Replicas) │      │   netflow.raw       │
└─────────────────────┘      └──────────┬──────────┘
                                        │
                                        ▼
                       ┌────────────────────────────┐
                       │   Spark Structured Stream  │
                       │   ─────────────────────    │
                       │   • Parse & Enrich         │
                       │   • Window Aggregations    │
                       │   • DDoS/Scan Detection    │
                       └─────────────┬──────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
        ┌──────────┐          ┌──────────┐          ┌──────────┐
        │  Bronze  │          │  Silver  │          │   Gold   │
        │  (Raw)   │          │(Enriched)│          │(Metrics) │
        └──────────┘          └──────────┘          └──────────┘
                                                          │
                                                          ▼
                                              ┌────────────────────┐
                                              │ Streamlit Dashboard│
                                              └────────────────────┘
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Producers** | Go 1.21+ (goroutines, channels, kafka-go) |
| **Streaming** | Apache Spark 3.x + PySpark |
| **Broker** | Kafka / Redpanda |
| **Storage** | Parquet (Bronze → Silver → Gold) |
| **Orchestration** | Docker + Docker Compose |
| **Dashboard** | Streamlit |
| **Monitoring** | Prometheus + Grafana (optional) |

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/netflow-ddos-spark.git
cd netflow-ddos-spark

# 2. Start the infrastructure
docker-compose up -d

# 3. View the dashboard
open http://localhost:8501
```

---

## 📁 Project Structure

```
netflow-ddos-spark/
├── README.md
├── docker/
│   ├── docker-compose.yml
│   ├── spark/
│   └── producer/
├── docs/
│   ├── PLAN.md              # Detailed execution plan
│   ├── design.md            # System design doc
│   └── experiments.md       # Performance benchmarks
├── producer-go/
│   ├── cmd/producer/
│   └── internal/
│       ├── config/
│       ├── netflow/
│       ├── kafka/
│       └── metrics/
├── spark-pyspark/
│   ├── src/
│   │   ├── streaming_job.py
│   │   ├── aggregates.py
│   │   └── detection.py
│   └── tests/
├── dashboard/
│   └── app.py
└── data/
    ├── bronze/
    ├── silver/
    └── gold/
```

---

## 📊 Detection Capabilities

| Alert Type | Description | Key Metrics |
|------------|-------------|-------------|
| **FAN_IN_DDOS** | Many sources → one destination | Unique sources, packets/sec, bytes/sec |
| **FAN_OUT_SCAN** | One source → many destinations | Unique destinations, port diversity |
| **SYN_BURST** | TCP SYN flood detection | SYN-only ratio per window |

---

## 📖 Documentation

- **[Execution Plan](docs/PLAN.md)** — Phase-by-phase implementation guide
- **[System Design](docs/design.md)** — Architecture decisions and trade-offs
- **[Experiments](docs/experiments.md)** — Performance benchmarks and scaling analysis

---

## 📝 Resume Bullets

> Use these to describe the project on your resume:

- Built a distributed NetFlow-style analytics pipeline using **Go producers** and **Apache Spark Structured Streaming** to process high-volume network telemetry in near real time
- Implemented event-time windowed aggregations and **DDoS/scan detection** with fault-tolerant checkpointing and partitioned Parquet sinks
- Mitigated hot-key data skew during fan-in attacks using **two-stage aggregation (key salting)**, improving pipeline stability under adversarial traffic patterns
- Benchmarked scaling across cluster sizes and event rates; analyzed shuffle bottlenecks and end-to-end alert latency using Spark streaming metrics

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
