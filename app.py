"""
Streamlit Web Application for Maintenance Scheduler.

Capacity-Constrained Preventive Maintenance and Asset Replacement Prioritization.
"""

from datetime import date, datetime, timedelta
import io
from pathlib import Path
import random
import sys
import time
import tracemalloc
from typing import List, Tuple

# Ensure current directory is accessible
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import altair as alt
import pandas as pd
import streamlit as st

from asset_manager import AssetManager
from config import (
    DEFAULT_DAILY_CAPACITY,
    DEFAULT_HORIZON_DAYS,
    REPLACEMENT_REPAIR_THRESHOLD,
    UPCOMING_WINDOW_DAYS,
)
from date_utils import format_date, parse_date
from input_handler import InputHandler, InputValidationError
from models import Asset
from replacement_analyzer import ReplacementAnalyzer
from reports import ReportGenerator
from scheduler import MaintenanceScheduler

# -----------------------------------------------------------------------------
# 1. Page Configuration & Theme
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Maintenance Scheduler",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Design System CSS
CUSTOM_CSS = """
<style>
/* Base Theme & Font */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"], .main {
    font-family: 'DM Sans', -apple-system, sans-serif !important;
}

code, pre, .mono {
    font-family: 'JetBrains Mono', monospace !important;
}

/* Metric Cards */
.kpi-container {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
}

.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.25rem 1.4rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    flex: 1;
    min-width: 180px;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
}

.metric-label {
    font-size: 0.8rem;
    color: #64748b;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 0.25rem;
}

.metric-value {
    font-size: 1.85rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.02em;
}

.metric-subtitle {
    font-size: 0.75rem;
    color: #94a3b8;
    margin-top: 0.35rem;
}

/* Badges */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-align: center;
}

.badge-red {
    color: #dc2626;
    background-color: #fee2e2;
    border: 1px solid #fecaca;
}

.badge-green {
    color: #16a34a;
    background-color: #dcfce7;
    border: 1px solid #bbf7d0;
}

.badge-amber {
    color: #d97706;
    background-color: #fef3c7;
    border: 1px solid #fde68a;
}

.badge-blue {
    color: #2563eb;
    background-color: #dbeafe;
    border: 1px solid #bfdbfe;
}

/* Key Output Callout */
.key-output-box {
    background-color: #0f172a;
    color: #f8fafc;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
    border-left: 5px solid #3b82f6;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.key-output-title {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin-bottom: 0.5rem;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. Sidebar Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ System Controls")
    st.markdown("Configure operational constraints & dataset.")

    st.markdown("#### 📅 Reference Date")
    selected_today = st.date_input(
        "Today's Calendar Date",
        value=date(2026, 10, 9),
        help="System date against which due dates and overdue statuses are evaluated.",
    )

    st.markdown("#### 👷 Technician Capacity")
    daily_capacity = st.number_input(
        "Daily Service Capacity (assets/day)",
        min_value=1,
        max_value=10000,
        value=DEFAULT_DAILY_CAPACITY,
        step=1,
        help="Maximum number of equipment maintenance services technicians can perform per day.",
    )

    st.markdown("#### 🔭 Scheduling Horizon")
    horizon_mode = st.radio(
        "Horizon Range",
        options=["Configured Horizon", "Unbounded (All Assets)"],
        index=0,
    )
    if horizon_mode == "Configured Horizon":
        horizon_days = st.slider(
            "Lookahead Horizon (days)",
            min_value=7,
            max_value=365,
            value=DEFAULT_HORIZON_DAYS,
            step=7,
        )
    else:
        horizon_days = None

    st.markdown("#### ⚠️ Replacement Threshold")
    replacement_threshold = st.number_input(
        "Repair Count Threshold",
        min_value=1,
        max_value=20,
        value=REPLACEMENT_REPAIR_THRESHOLD,
        step=1,
        help="Historical breakdown count triggering replacement review.",
    )

    st.markdown("---")
    st.markdown("#### 📂 Data Source")
    data_source = st.selectbox(
        "Choose Input Method",
        options=[
            "Standard Sample Dataset (3 Assets)",
            "Upload Custom Input File",
            "Manual Text Input",
            "Generate Synthetic Fleet",
        ],
    )


# -----------------------------------------------------------------------------
# 3. Data Ingestion
# -----------------------------------------------------------------------------
DEFAULT_SAMPLE_RAW = """2026-10-09
3
A101 180 2026-03-01 1
A102 90 2026-08-01 3
A103 365 2026-01-15 0"""


def generate_synthetic(n: int, ref_date: date) -> List[Asset]:
    rng = random.Random(42)
    intervals = [30, 60, 90, 180, 365]
    assets: List[Asset] = []
    for i in range(1, n + 1):
        asset_id = f"EQ_{i:05d}"
        interval = intervals[i % len(intervals)]
        days_ago = rng.randint(10, 400)
        last_service = ref_date - timedelta(days=days_ago)
        repairs = rng.choices([0, 1, 2, 3, 4, 5], weights=[40, 25, 15, 12, 5, 3])[0]
        assets.append(Asset(asset_id, interval, last_service, repairs))
    return assets


assets: List[Asset] = []
today = selected_today
error_msg = None

if data_source == "Standard Sample Dataset (3 Assets)":
    today, assets = InputHandler.parse_lines(DEFAULT_SAMPLE_RAW.splitlines())

elif data_source == "Upload Custom Input File":
    uploaded = st.sidebar.file_uploader("Upload .txt maintenance data", type=["txt"])
    if uploaded is not None:
        try:
            content = uploaded.getvalue().decode("utf-8")
            today, assets = InputHandler.parse_lines(content.splitlines())
        except Exception as e:
            error_msg = f"File Parsing Error: {e}"
    else:
        st.info("👆 Please upload a valid text file or select 'Standard Sample Dataset'.")
        today, assets = InputHandler.parse_lines(DEFAULT_SAMPLE_RAW.splitlines())

elif data_source == "Manual Text Input":
    text_data = st.sidebar.text_area(
        "Paste formatted text lines:",
        value=DEFAULT_SAMPLE_RAW,
        height=180,
    )
    if text_data.strip():
        try:
            today, assets = InputHandler.parse_lines(text_data.splitlines())
        except Exception as e:
            error_msg = f"Validation Error: {e}"

elif data_source == "Generate Synthetic Fleet":
    fleet_size = st.sidebar.select_slider(
        "Fleet Size",
        options=[10, 50, 250, 1000, 5000, 20000, 100000],
        value=50,
    )
    if st.sidebar.button("Generate Assets", use_container_width=True):
        st.session_state["fleet_size"] = fleet_size
    active_size = st.session_state.get("fleet_size", fleet_size)
    assets = generate_synthetic(active_size, today)


# -----------------------------------------------------------------------------
# 4. Pipeline Execution
# -----------------------------------------------------------------------------
st.title("🛠️ Maintenance Scheduler Dashboard")
st.markdown(
    "**Capacity-Constrained Preventive Maintenance & Asset Replacement Prioritization** | "
    f"Evaluating fleet state for reference date: `{today}`"
)

if error_msg:
    st.error(error_msg)
    st.stop()

# Run Core Algorithms
overdue_assets = AssetManager.get_overdue_assets(assets, today)
replacement_candidates = ReplacementAnalyzer.analyze(
    assets,
    today=today,
    threshold=replacement_threshold,
)
upcoming_assets = AssetManager.get_upcoming_assets(
    assets,
    today=today,
    window_days=UPCOMING_WINDOW_DAYS,
)

scheduler = MaintenanceScheduler(
    daily_capacity=daily_capacity,
    horizon_days=horizon_days,
)
schedule_result = scheduler.schedule(assets, today=today)


# -----------------------------------------------------------------------------
# 5. Mandatory Key Output Callout
# -----------------------------------------------------------------------------
key_records = ReportGenerator.format_key_records(
    overdue_assets=overdue_assets,
    replacement_candidates=replacement_candidates,
    today=today,
)

st.markdown(
    f"""
    <div class="key-output-box">
        <div class="key-output-title">Mandatory System Output Records (Section 6 Specification)</div>
        <div>{key_records.replace(chr(10), '<br>') if key_records else 'NO OVERDUE OR REPLACEMENT ASSETS IDENTIFIED'}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# 6. KPI Metric Cards
# -----------------------------------------------------------------------------
kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

with kpi1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Total Assets</div>
            <div class="metric-value">{len(assets):,}</div>
            <div class="metric-subtitle">Tracked machinery</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Overdue Assets</div>
            <div class="metric-value" style="color: {'#dc2626' if overdue_assets else '#16a34a'};">
                {len(overdue_assets):,}
            </div>
            <div class="metric-subtitle">Past service due date</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Replacement Alerts</div>
            <div class="metric-value" style="color: {'#d97706' if replacement_candidates else '#64748b'};">
                {len(replacement_candidates):,}
            </div>
            <div class="metric-subtitle">Repairs ≥ {replacement_threshold}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Scheduled Services</div>
            <div class="metric-value">{schedule_result.total_scheduled:,}</div>
            <div class="metric-subtitle">Capacity: {daily_capacity}/day</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Total Lateness</div>
            <div class="metric-value">{schedule_result.total_lateness:,} <span style="font-size:1rem;color:#64748b;">days</span></div>
            <div class="metric-subtitle">Cumulative delay</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi6:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Max Lateness (L_max)</div>
            <div class="metric-value" style="color: {'#dc2626' if schedule_result.max_lateness > 0 else '#16a34a'};">
                {schedule_result.max_lateness:,} <span style="font-size:1rem;color:#64748b;">days</span>
            </div>
            <div class="metric-subtitle">Peak asset delay</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 7. Analytical Tabs
# -----------------------------------------------------------------------------
tab_sched, tab_overdue, tab_replace, tab_upcoming, tab_benchmark = st.tabs([
    "📅 Capacity-Constrained Schedule",
    "🚨 Overdue Maintenance Queue",
    "🔄 Replacement Prioritization",
    "⏳ Due in 30 Days (Upcoming)",
    "⚡ 100k Benchmark & Performance",
])

# ----------------- TAB 1: Capacity Schedule -----------------
with tab_sched:
    st.subheader("Capacity-Constrained EDF Daily Service Schedule")
    st.markdown(
        f"Technicians process up to **{daily_capacity} assets per day** using **Earliest Deadline First (EDF)** dispatching. "
        f"Horizon: **{horizon_days if horizon_days else 'Unbounded'} days**."
    )

    if schedule_result.total_scheduled > 0:
        # Schedule timeline aggregation
        daily_counts = [
            {"date": str(d), "services": len(services), "capacity": daily_capacity}
            for d, services in sorted(schedule_result.daily_schedule.items())
        ]
        df_daily = pd.DataFrame(daily_counts)

        # Show chart of daily capacity utilization
        if not df_daily.empty:
            chart = alt.Chart(df_daily).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#3b82f6").encode(
                x=alt.X("date:T", title="Scheduled Calendar Date"),
                y=alt.Y("services:Q", title="Services Assigned"),
                tooltip=["date", "services", "capacity"],
            ).properties(height=240, title="Daily Technician Service Volume")
            st.altair_chart(chart, use_container_width=True)

        # Detailed table of scheduled services
        st.markdown("#### Scheduled Service Queue")
        sched_data = []
        for svc in schedule_result.services[:1000]:  # Limit preview to 1000 for browser responsiveness
            sched_data.append({
                "Asset ID": svc.asset.asset_id,
                "Due Date": str(svc.due_date),
                "Scheduled Date": str(svc.scheduled_date),
                "Lateness (Days)": svc.lateness,
                "Status": "ON TIME" if svc.lateness == 0 else f"LATE ({svc.lateness}d)",
            })
        df_sched_table = pd.DataFrame(sched_data)
        st.dataframe(df_sched_table, use_container_width=True, height=350)
        if len(schedule_result.services) > 1000:
            st.caption(f"Showing first 1,000 of {schedule_result.total_scheduled:,} scheduled services.")
    else:
        st.info("No services scheduled within current parameters.")


# ----------------- TAB 2: Overdue Assets -----------------
with tab_overdue:
    st.subheader("Overdue Equipment Roster")
    st.markdown("Equipment with `next_due_date < today`, deterministically sorted by earliest due date.")

    if overdue_assets:
        overdue_data = []
        for a in overdue_assets:
            overdue_data.append({
                "Asset ID": a.asset_id,
                "Next Due Date": str(a.next_due_date),
                "Days Overdue": a.days_overdue(today),
                "Operating Interval (Days)": a.interval_days,
                "Last Service Date": str(a.last_service_date),
                "Historical Repairs": a.repairs,
            })
        df_overdue = pd.DataFrame(overdue_data)
        st.dataframe(df_overdue, use_container_width=True, height=350)
    else:
        st.success("🎉 All equipment assets are operating within schedule! No overdue maintenance required.")


# ----------------- TAB 3: Replacement Candidates -----------------
with tab_replace:
    st.subheader("Replacement Candidates & Urgency Prioritization")
    st.markdown(
        rf"Assets with historical repairs $\ge {replacement_threshold}$. "
        r"Ranked by **Urgency Score**: $\text{failure\_rate} \times (1.5 \text{ if overdue else } 1.0) + \frac{\text{days\_overdue}}{30.0}$."
    )

    if replacement_candidates:
        cand_data = []
        for rank, c in enumerate(replacement_candidates, start=1):
            cand_data.append({
                "Priority Rank": rank,
                "Asset ID": c.asset.asset_id,
                "Historical Repairs": c.repairs,
                "Failure Rate (rep/yr)": round(c.failure_rate, 2),
                "Is Overdue?": "YES" if c.is_overdue else "No",
                "Days Overdue": c.days_overdue,
                "Urgency Score": round(c.urgency_score, 2),
                "Next Due Date": str(c.asset.next_due_date),
            })
        df_cands = pd.DataFrame(cand_data)
        st.dataframe(df_cands, use_container_width=True, height=350)
    else:
        st.success("No assets meet the replacement threshold criteria.")


# ----------------- TAB 4: Due in 30 Days -----------------
with tab_upcoming:
    st.subheader("Preventive Maintenance Due in Next 30 Days (Feature F)")
    st.markdown(r"Assets with next service date between today and 30 days from today ($0 \le \text{days\_remaining} \le 30$).")

    if upcoming_assets:
        upcoming_data = []
        for a in upcoming_assets:
            upcoming_data.append({
                "Asset ID": a.asset_id,
                "Next Due Date": str(a.next_due_date),
                "Days Remaining": a.days_remaining(today),
                "Historical Repairs": a.repairs,
                "Replacement Candidate": "YES (REPLACE)" if a.is_replacement_candidate() else "No",
            })
        df_upcoming = pd.DataFrame(upcoming_data)
        st.dataframe(df_upcoming, use_container_width=True, height=350)
    else:
        st.info("No equipment scheduled for service within the next 30 calendar days.")


# ----------------- TAB 5: Live Benchmark -----------------
with tab_benchmark:
    st.subheader("⚡ Live 100,000 Asset Performance Benchmark")
    st.markdown(
        "Demonstrates real-world $O(N \\log N)$ scalability on synthetic industrial fleets. "
        "Measures live execution time, throughput, and memory allocations via `tracemalloc`."
    )

    test_n = st.selectbox("Benchmark Fleet Size", [10000, 50000, 100000], index=2)
    test_cap = st.number_input("Benchmark Daily Capacity", min_value=10, max_value=2000, value=250)

    if st.button("🚀 Run Live Benchmark", type="primary"):
        with st.spinner(f"Generating and scheduling {test_n:,} equipment assets..."):
            tracemalloc.start()
            t_start = time.perf_counter()

            # Generation
            synth_assets = generate_synthetic(test_n, today)
            t_gen = time.perf_counter() - t_start

            # Overdue
            t0 = time.perf_counter()
            b_overdue = AssetManager.get_overdue_assets(synth_assets, today)
            t_overdue = time.perf_counter() - t0

            # Replacement
            t0 = time.perf_counter()
            b_cands = ReplacementAnalyzer.analyze(synth_assets, today)
            t_replace = time.perf_counter() - t0

            # Scheduling
            t0 = time.perf_counter()
            b_sched = MaintenanceScheduler(daily_capacity=test_cap, horizon_days=60)
            b_res = b_sched.schedule(synth_assets, today)
            t_sched = time.perf_counter() - t0

            total_elapsed = time.perf_counter() - t_start
            _, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            peak_mb = peak_mem / (1024 * 1024)
            throughput = test_n / total_elapsed

            st.success(f"✅ Successfully processed {test_n:,} assets in {total_elapsed:.3f} seconds!")

            b_col1, b_col2, b_col3, b_col4 = st.columns(4)
            with b_col1:
                st.metric("Total Execution Time", f"{total_elapsed:.3f} s")
            with b_col2:
                st.metric("Throughput", f"{throughput:,.0f} assets/s")
            with b_col3:
                st.metric("Peak Memory", f"{peak_mb:.2f} MB")
            with b_col4:
                st.metric("Services Scheduled", f"{b_res.total_scheduled:,}")

            st.markdown("#### Phase Breakdown:")
            st.write({
                "Phase 1: Generation & Instantiation": f"{t_gen:.4f} s",
                "Phase 2: Overdue Filtering & Deterministic Sort": f"{t_overdue:.4f} s ({len(b_overdue):,} overdue)",
                "Phase 3: Replacement Triaging & Ranking": f"{t_replace:.4f} s ({len(b_cands):,} candidates)",
                "Phase 4: Capacity-Constrained EDF Scheduling": f"{t_sched:.4f} s ({b_res.total_scheduled:,} scheduled)",
            })
