"""Schema definitions for NetFlow records."""

from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    LongType,
    TimestampType,
)

# Schema for raw NetFlow records from Kafka
NETFLOW_SCHEMA = StructType([
    StructField("ts", TimestampType(), True),
    StructField("router_id", StringType(), True),
    StructField("src_ip", StringType(), True),
    StructField("dst_ip", StringType(), True),
    StructField("src_port", IntegerType(), True),
    StructField("dst_port", IntegerType(), True),
    StructField("proto", StringType(), True),
    StructField("bytes", LongType(), True),
    StructField("packets", IntegerType(), True),
    StructField("tcp_flags", StringType(), True),
    StructField("sampling_rate", IntegerType(), True),
])
