"""
Spark Structured Streaming job for NetFlow analytics.

This job:
1. Reads raw NetFlow records from Kafka
2. Writes to Bronze layer (raw Parquet)
3. Enriches to Silver layer (with derived fields)
4. Aggregates to Gold layer (windowed metrics)
"""

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_date

from schemas import NETFLOW_SCHEMA
from enrichment import enrich_netflow
from aggregates import (
    aggregate_top_destinations,
    aggregate_top_talkers,
    aggregate_router_summary
)
from detection import (
    detect_fan_in_ddos,
    detect_fan_out_scan
)


def create_spark_session():
    """Create and configure Spark session."""
    return (
        SparkSession.builder
        .appName("NetFlowAnalyzer")
        .config("spark.sql.streaming.checkpointLocation", "/data/checkpoints")
        .config("spark.sql.shuffle.partitions", "12")
        .getOrCreate()
    )


def read_from_kafka(spark, kafka_brokers: str, topic: str):
    """Read streaming data from Kafka."""
    return (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", kafka_brokers)
        .option("subscribe", topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )


def parse_netflow(kafka_df):
    """Parse JSON NetFlow records from Kafka messages."""
    return (
        kafka_df
        .select(
            from_json(
                col("value").cast("string"),
                NETFLOW_SCHEMA
            ).alias("data")
        )
        .select("data.*")
        .filter(col("ts").isNotNull())  # Filter out malformed records
    )


def write_bronze(df, output_path: str, checkpoint_path: str):
    """Write raw records to Bronze layer as Parquet."""
    return (
        df.writeStream
        .format("parquet")
        .option("path", output_path)
        .option("checkpointLocation", checkpoint_path)
        .outputMode("append")
        .trigger(processingTime="10 seconds")
        .start()
    )


def write_silver(df, output_path: str, checkpoint_path: str):
    """Write enriched records to Silver layer as Parquet, partitioned by date."""
    return (
        df
        .withColumn("date", to_date(col("ts")))
        .writeStream
        .format("parquet")
        .option("path", output_path)
        .option("checkpointLocation", checkpoint_path)
        .partitionBy("date")
        .outputMode("append")
        .trigger(processingTime="10 seconds")
        .start()
    )


def write_gold_aggregates(df, output_path: str, checkpoint_path: str):
    """Write windowed aggregates to Gold layer as Parquet."""
    return (
        df.writeStream
        .format("parquet")
        .option("path", output_path)
        .option("checkpointLocation", checkpoint_path)
        .outputMode("append")
        .trigger(processingTime="10 seconds")
        .start()
    )


def main():
    # Configuration from environment
    kafka_brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
    topic = os.getenv("KAFKA_TOPIC", "netflow.raw")
    bronze_path = os.getenv("BRONZE_PATH", "/data/bronze/netflow")
    bronze_checkpoint = os.getenv("CHECKPOINT_PATH", "/data/checkpoints/bronze")
    silver_path = os.getenv("SILVER_PATH", "/data/silver/netflow_enriched")
    silver_checkpoint = os.getenv("SILVER_CHECKPOINT", "/data/checkpoints/silver")

    # Gold layer paths
    gold_base = os.getenv("GOLD_PATH", "/data/gold")
    top_destinations_path = f"{gold_base}/top_destinations"
    top_talkers_path = f"{gold_base}/top_talkers"
    router_summary_path = f"{gold_base}/router_summary"
    alerts_path = f"{gold_base}/alerts"

    print(f"Starting NetFlow Streaming Job")
    print(f"  Kafka Brokers: {kafka_brokers}")
    print(f"  Topic: {topic}")
    print(f"  Bronze Path: {bronze_path}")
    print(f"  Silver Path: {silver_path}")
    print(f"  Gold Path: {gold_base}")
    print(f"  Alerts Path: {alerts_path}")

    # Create Spark session
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    # Build streaming pipeline
    kafka_df = read_from_kafka(spark, kafka_brokers, topic)
    parsed_df = parse_netflow(kafka_df)

    # Write to Bronze (raw data)
    bronze_query = write_bronze(parsed_df, bronze_path, bronze_checkpoint)

    # Enrich and write to Silver
    enriched_df = enrich_netflow(parsed_df)
    silver_query = write_silver(enriched_df, silver_path, silver_checkpoint)

    # Compute Gold layer aggregations
    top_destinations = aggregate_top_destinations(enriched_df)
    top_talkers = aggregate_top_talkers(enriched_df)
    router_summary = aggregate_router_summary(enriched_df)

    # Write Gold layer outputs
    top_dest_query = write_gold_aggregates(
        top_destinations,
        top_destinations_path,
        f"/data/checkpoints/gold_top_destinations"
    )

    top_talkers_query = write_gold_aggregates(
        top_talkers,
        top_talkers_path,
        f"/data/checkpoints/gold_top_talkers"
    )

    router_query = write_gold_aggregates(
        router_summary,
        router_summary_path,
        f"/data/checkpoints/gold_router_summary"
    )

    # Detection: Apply detection rules to aggregates
    ddos_alerts = detect_fan_in_ddos(top_destinations)
    scan_alerts = detect_fan_out_scan(top_talkers)

    # Union all alerts
    all_alerts = ddos_alerts.union(scan_alerts)

    # Write alerts
    alerts_query = write_gold_aggregates(
        all_alerts,
        alerts_path,
        f"/data/checkpoints/gold_alerts"
    )

    print("Streaming job started (Bronze + Silver + Gold + Alerts). Waiting for data...")

    # Wait for termination
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
