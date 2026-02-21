"""
DDoS and scan detection rules.

Detection types:
- FAN_IN_DDOS: Many sources attacking one destination
- FAN_OUT_SCAN: One source probing many destinations
- SYN_BURST: TCP SYN flood detection
"""

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col,
    lit,
    when,
    current_timestamp,
)


# Detection thresholds
DDOS_UNIQUE_SOURCES_THRESHOLD = 100
DDOS_PACKETS_THRESHOLD = 10000
DDOS_BYTES_THRESHOLD = 10_000_000

SCAN_UNIQUE_DESTINATIONS_THRESHOLD = 50
SCAN_DISTINCT_PORTS_THRESHOLD = 20


def detect_fan_in_ddos(top_destinations_df: DataFrame) -> DataFrame:
    """
    Detect fan-in DDoS attacks.

    Triggers when a destination receives traffic from many unique sources
    with high packet/byte counts.
    """
    severity = (
        when(col("unique_sources") > 500, 1.0)
        .when(col("unique_sources") > 200, 0.7)
        .otherwise(0.4)
    )

    return (
        top_destinations_df
        .filter(
            (col("unique_sources") > DDOS_UNIQUE_SOURCES_THRESHOLD) &
            (
                (col("total_packets") > DDOS_PACKETS_THRESHOLD) |
                (col("total_bytes") > DDOS_BYTES_THRESHOLD)
            )
        )
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            lit("FAN_IN_DDOS").alias("alert_type"),
            col("dst_ip").alias("entity"),
            severity.alias("severity_score"),
            col("unique_sources"),
            col("total_packets"),
            col("total_bytes"),
            current_timestamp().alias("detected_at"),
        )
    )


def detect_fan_out_scan(top_talkers_df: DataFrame) -> DataFrame:
    """
    Detect fan-out port scans.

    Triggers when a source contacts many unique destinations
    across many different ports.
    """
    severity = (
        when(col("unique_destinations") > 200, 1.0)
        .when(col("unique_destinations") > 100, 0.7)
        .otherwise(0.4)
    )

    return (
        top_talkers_df
        .filter(
            (col("unique_destinations") > SCAN_UNIQUE_DESTINATIONS_THRESHOLD) &
            (col("distinct_ports") > SCAN_DISTINCT_PORTS_THRESHOLD)
        )
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            lit("FAN_OUT_SCAN").alias("alert_type"),
            col("src_ip").alias("entity"),
            severity.alias("severity_score"),
            col("unique_destinations").alias("unique_sources"),  # Repurpose column
            col("total_packets"),
            col("total_bytes"),
            current_timestamp().alias("detected_at"),
        )
    )
