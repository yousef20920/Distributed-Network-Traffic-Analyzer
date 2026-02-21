"""
Gold layer windowed aggregations.

Computes real-time metrics over tumbling windows:
- Top talkers (by source IP)
- Top destinations (by destination IP)
- Router summary
"""

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col,
    sum as spark_sum,
    count,
    approx_count_distinct,
    window,
    collect_set,
    size,
)


def aggregate_top_destinations(
    df: DataFrame,
    window_duration: str = "1 minute",
    watermark: str = "2 minutes"
) -> DataFrame:
    """
    Aggregate traffic by destination IP per window.
    Key metric for detecting fan-in DDoS attacks.
    """
    return (
        df
        .withWatermark("ts", watermark)
        .groupBy(
            window("ts", window_duration),
            "dst_ip"
        )
        .agg(
            spark_sum("bytes").alias("total_bytes"),
            spark_sum("packets").alias("total_packets"),
            count("*").alias("flow_count"),
            approx_count_distinct("src_ip").alias("unique_sources"),
        )
    )


def aggregate_top_talkers(
    df: DataFrame,
    window_duration: str = "1 minute",
    watermark: str = "2 minutes"
) -> DataFrame:
    """
    Aggregate traffic by source IP per window.
    Key metric for detecting fan-out scans.
    """
    return (
        df
        .withWatermark("ts", watermark)
        .groupBy(
            window("ts", window_duration),
            "src_ip"
        )
        .agg(
            spark_sum("bytes").alias("total_bytes"),
            spark_sum("packets").alias("total_packets"),
            count("*").alias("flow_count"),
            approx_count_distinct("dst_ip").alias("unique_destinations"),
            approx_count_distinct("dst_port").alias("distinct_ports"),
        )
    )


def aggregate_router_summary(
    df: DataFrame,
    window_duration: str = "1 minute",
    watermark: str = "2 minutes"
) -> DataFrame:
    """Aggregate traffic by router per window."""
    return (
        df
        .withWatermark("ts", watermark)
        .groupBy(
            window("ts", window_duration),
            "router_id"
        )
        .agg(
            spark_sum("bytes").alias("total_bytes"),
            spark_sum("packets").alias("total_packets"),
            count("*").alias("flow_count"),
            approx_count_distinct("src_ip").alias("unique_sources"),
            approx_count_distinct("dst_ip").alias("unique_destinations"),
        )
    )
