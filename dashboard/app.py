"""
Streamlit Dashboard for NetFlow Analytics.

Displays:
- Live metrics (top destinations, top talkers)
- Real-time alerts feed
- System health indicators
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

# Configuration
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
BRONZE_PATH = DATA_DIR / "bronze" / "netflow"
SILVER_PATH = DATA_DIR / "silver" / "netflow_enriched"
GOLD_PATH = DATA_DIR / "gold"
ALERTS_PATH = GOLD_PATH / "alerts"
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "5"))

st.set_page_config(
    page_title="NetFlow Analyzer",
    page_icon="🌐",
    layout="wide",
)


def load_parquet_data(path: Path, limit: int = 1000) -> pd.DataFrame:
    """Load latest data from Parquet files."""
    if not path.exists():
        return pd.DataFrame()

    parquet_files = list(path.glob("**/*.parquet"))
    if not parquet_files:
        return pd.DataFrame()

    # Sort by modification time, get newest
    parquet_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    try:
        # Read most recent files
        dfs = []
        for f in parquet_files[:10]:
            dfs.append(pd.read_parquet(f))
        if dfs:
            df = pd.concat(dfs, ignore_index=True)
            return df.tail(limit)
    except Exception as e:
        st.error(f"Error reading data: {e}")

    return pd.DataFrame()


def load_gold_aggregates(path: Path, limit: int = 100) -> pd.DataFrame:
    """Load Gold layer aggregates."""
    if not path.exists():
        return pd.DataFrame()

    parquet_files = list(path.glob("*.parquet"))
    if not parquet_files:
        return pd.DataFrame()

    try:
        dfs = []
        for f in parquet_files[:20]:
            df = pd.read_parquet(f)
            if len(df) > 0:
                dfs.append(df)

        if dfs:
            df = pd.concat(dfs, ignore_index=True)
            # Extract window start/end if window column exists
            if 'window' in df.columns:
                df['window_start'] = df['window'].apply(lambda x: x['start'] if isinstance(x, dict) else x.start)
                df['window_end'] = df['window'].apply(lambda x: x['end'] if isinstance(x, dict) else x.end)
                df['window_start'] = pd.to_datetime(df['window_start'])
                df['window_end'] = pd.to_datetime(df['window_end'])
            return df.tail(limit)
    except Exception as e:
        st.error(f"Error reading gold data from {path}: {e}")

    return pd.DataFrame()


def get_recent_alerts(minutes: int = 5) -> pd.DataFrame:
    """Get alerts from the last N minutes."""
    alerts_df = load_parquet_data(ALERTS_PATH, limit=500)
    if alerts_df.empty:
        return pd.DataFrame()

    # Filter for recent alerts
    if 'detected_at' in alerts_df.columns:
        cutoff = datetime.now() - timedelta(minutes=minutes)
        alerts_df['detected_at'] = pd.to_datetime(alerts_df['detected_at'])
        recent = alerts_df[alerts_df['detected_at'] > cutoff]
        return recent.sort_values('detected_at', ascending=False)

    return alerts_df


def main():
    st.title("🌐 Distributed NetFlow Analyzer")
    st.markdown("Real-time network traffic analytics and DDoS detection")

    # Check for active alerts
    recent_alerts = get_recent_alerts(minutes=5)

    if not recent_alerts.empty:
        # ATTACK WARNING BANNER
        st.error("🚨 **SECURITY ALERT: ATTACK DETECTED!**")

        # Show alert summary
        col1, col2, col3 = st.columns(3)
        with col1:
            attack_type = recent_alerts.iloc[0]['alert_type']
            st.metric("Attack Type", attack_type)
        with col2:
            target = recent_alerts.iloc[0]['entity']
            st.metric("Target/Source", target)
        with col3:
            severity = recent_alerts.iloc[0]['severity_score']
            severity_label = "🔴 CRITICAL" if severity >= 0.8 else "🟠 HIGH" if severity >= 0.6 else "🟡 MEDIUM"
            st.metric("Severity", severity_label)

        st.divider()

    # Sidebar
    st.sidebar.header("Settings")
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)

    if auto_refresh:
        st.sidebar.info(f"Refreshing every {REFRESH_INTERVAL}s")

    # Layer selector
    st.sidebar.header("Data Layer")
    layer = st.sidebar.radio(
        "Select Layer",
        ["🥇 Gold (Aggregations)", "🥈 Silver (Enriched)", "🥉 Bronze (Raw)", "🚨 Alerts"],
        index=0
    )

    # Metrics cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if not recent_alerts.empty:
            st.metric("Status", "🔴 ATTACK", delta="Active")
        else:
            st.metric("Status", "🟢 Normal")

    with col2:
        bronze_files = list(BRONZE_PATH.glob("**/*.parquet")) if BRONZE_PATH.exists() else []
        st.metric("Bronze Files", len(bronze_files))

    with col3:
        silver_files = list(SILVER_PATH.glob("**/*.parquet")) if SILVER_PATH.exists() else []
        st.metric("Silver Files", len(silver_files))

    with col4:
        all_alerts = load_parquet_data(ALERTS_PATH, limit=1000)
        st.metric("Total Alerts", len(all_alerts), delta=f"{len(recent_alerts)} recent" if not recent_alerts.empty else None)

    st.divider()

    # Display based on layer selection
    if layer == "🥇 Gold (Aggregations)":
        show_gold_layer()
    elif layer == "🥈 Silver (Enriched)":
        show_silver_layer()
    elif layer == "🥉 Bronze (Raw)":
        show_bronze_layer()
    else:
        show_alerts()

    # Auto-refresh
    if auto_refresh:
        time.sleep(REFRESH_INTERVAL)
        st.rerun()


def show_gold_layer():
    """Display Gold layer windowed aggregations."""
    st.header("📊 Gold Layer - Windowed Aggregations (1-minute windows)")

    # Top Destinations
    st.subheader("🎯 Top Destinations (by bytes)")
    top_dest_path = GOLD_PATH / "top_destinations"
    top_dest = load_gold_aggregates(top_dest_path, limit=50)

    if not top_dest.empty:
        # Sort by total_bytes and show top 20
        display_df = top_dest.nlargest(20, 'total_bytes')[
            ['dst_ip', 'total_bytes', 'total_packets', 'flow_count', 'unique_sources']
        ]

        # Highlight potential attack targets (>100 sources)
        def highlight_attacks(row):
            if row['unique_sources'] > 100:
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)

        styled_df = display_df.style.apply(highlight_attacks, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # Show a chart
        chart_data = top_dest.nlargest(10, 'total_bytes')[['dst_ip', 'total_bytes']]
        st.bar_chart(chart_data.set_index('dst_ip'))
    else:
        st.info("No top destinations data yet. Waiting for windows to complete (2-minute watermark)...")

    st.divider()

    # Top Talkers
    st.subheader("💬 Top Talkers (by bytes)")
    top_talkers_path = GOLD_PATH / "top_talkers"
    top_talkers = load_gold_aggregates(top_talkers_path, limit=50)

    if not top_talkers.empty:
        display_df = top_talkers.nlargest(20, 'total_bytes')[
            ['src_ip', 'total_bytes', 'total_packets', 'unique_destinations', 'distinct_ports']
        ]

        # Highlight potential scanners (>50 destinations)
        def highlight_scanners(row):
            if row['unique_destinations'] > 50:
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)

        styled_df = display_df.style.apply(highlight_scanners, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # Show a chart
        chart_data = top_talkers.nlargest(10, 'total_bytes')[['src_ip', 'total_bytes']]
        st.bar_chart(chart_data.set_index('src_ip'))
    else:
        st.info("No top talkers data yet. Waiting for windows to complete...")

    st.divider()

    # Router Summary
    st.subheader("🖥️ Router Summary")
    router_path = GOLD_PATH / "router_summary"
    router_summary = load_gold_aggregates(router_path, limit=10)

    if not router_summary.empty:
        display_df = router_summary[
            ['router_id', 'total_bytes', 'total_packets', 'flow_count',
             'unique_sources', 'unique_destinations']
        ]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No router summary data yet.")


def show_silver_layer():
    """Display Silver layer enriched flows."""
    st.header("🥈 Silver Layer - Enriched NetFlow Records")

    flows_df = load_parquet_data(SILVER_PATH, limit=100)

    if not flows_df.empty:
        st.info(f"Showing {len(flows_df)} most recent enriched flows")

        # Show enriched fields
        display_cols = ['ts', 'src_ip', 'dst_ip', 'src_subnet_24', 'dst_subnet_24',
                       'is_private_src', 'is_private_dst', 'dst_port', 'dst_service',
                       'proto', 'bytes', 'packets']

        available_cols = [col for col in display_cols if col in flows_df.columns]
        st.dataframe(flows_df[available_cols].tail(50), use_container_width=True, hide_index=True)

        # Show service distribution
        if 'dst_service' in flows_df.columns:
            st.subheader("📈 Service Distribution")
            service_counts = flows_df['dst_service'].value_counts().head(10)
            st.bar_chart(service_counts)
    else:
        st.info("No enriched flow data available yet.")


def show_bronze_layer():
    """Display Bronze layer raw flows."""
    st.header("🥉 Bronze Layer - Raw NetFlow Records")

    flows_df = load_parquet_data(BRONZE_PATH, limit=100)

    if not flows_df.empty:
        st.info(f"Showing {len(flows_df)} most recent raw flows")
        st.dataframe(flows_df.tail(50), use_container_width=True, hide_index=True)
    else:
        st.info("No flow data available yet. Start the producer to generate traffic.")


def show_alerts():
    """Display alerts."""
    st.header("🚨 Security Alerts")

    alerts_df = load_parquet_data(ALERTS_PATH, limit=200)

    if not alerts_df.empty:
        st.success(f"Found {len(alerts_df)} alerts")

        # Add color coding
        def color_by_severity(row):
            severity = row['severity_score']
            if severity >= 0.8:
                return ['background-color: #ff4444; color: white'] * len(row)
            elif severity >= 0.6:
                return ['background-color: #ffaa44'] * len(row)
            else:
                return ['background-color: #ffff44'] * len(row)

        # Format timestamp
        if 'detected_at' in alerts_df.columns:
            alerts_df['detected_at'] = pd.to_datetime(alerts_df['detected_at'])
            alerts_df = alerts_df.sort_values('detected_at', ascending=False)

        if 'window_start' in alerts_df.columns:
            alerts_df['window_start'] = pd.to_datetime(alerts_df['window_start'])

        styled_df = alerts_df[['alert_type', 'entity', 'severity_score', 'unique_sources',
                               'total_packets', 'total_bytes', 'window_start', 'detected_at']].style.apply(color_by_severity, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # Alert statistics
        st.subheader("📊 Alert Statistics")
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Total Alerts", len(alerts_df))
            alert_types = alerts_df['alert_type'].value_counts()
            st.bar_chart(alert_types)

        with col2:
            if not alerts_df.empty:
                avg_severity = alerts_df['severity_score'].mean()
                st.metric("Average Severity", f"{avg_severity:.2f}")

                # Most targeted entities
                if 'entity' in alerts_df.columns:
                    top_targets = alerts_df['entity'].value_counts().head(5)
                    st.write("**Most Targeted:**")
                    st.dataframe(top_targets, use_container_width=True)
    else:
        st.success("✅ No alerts detected. System operating normally.")


if __name__ == "__main__":
    main()
