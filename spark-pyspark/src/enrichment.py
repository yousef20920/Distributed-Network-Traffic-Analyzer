"""
Silver layer enrichment transformations.

Adds derived fields for analytics:
- Subnet extraction
- Private IP classification
- Service mapping
"""

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col,
    when,
    regexp_extract,
    lit,
)


def extract_subnet(ip_col: str, output_col: str):
    """Extract /24 subnet from IP address."""
    return regexp_extract(col(ip_col), r"^(\d+\.\d+\.\d+)\.\d+$", 1).alias(output_col)


def is_private_ip(ip_col: str):
    """Check if IP is in RFC 1918 private range."""
    return (
        col(ip_col).startswith("10.") |
        col(ip_col).startswith("192.168.") |
        col(ip_col).rlike(r"^172\.(1[6-9]|2[0-9]|3[0-1])\.")
    )


def map_service(port_col: str):
    """Map common ports to service names."""
    return (
        when(col(port_col) == 80, "HTTP")
        .when(col(port_col) == 443, "HTTPS")
        .when(col(port_col) == 22, "SSH")
        .when(col(port_col) == 53, "DNS")
        .when(col(port_col) == 21, "FTP")
        .when(col(port_col) == 25, "SMTP")
        .when(col(port_col) == 3306, "MySQL")
        .when(col(port_col) == 5432, "PostgreSQL")
        .when(col(port_col) == 6379, "Redis")
        .when(col(port_col) == 8080, "HTTP-ALT")
        .otherwise("OTHER")
    )


def enrich_netflow(df: DataFrame) -> DataFrame:
    """Apply all enrichment transformations."""
    return (
        df
        .withColumn("src_subnet_24", extract_subnet("src_ip", "src_subnet_24"))
        .withColumn("dst_subnet_24", extract_subnet("dst_ip", "dst_subnet_24"))
        .withColumn("is_private_src", is_private_ip("src_ip"))
        .withColumn("is_private_dst", is_private_ip("dst_ip"))
        .withColumn("dst_service", map_service("dst_port"))
    )
