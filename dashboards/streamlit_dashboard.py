"""
MODULE 8 — DASHBOARD VISUALIZATION
Streamlit-based real-time monitoring dashboard.

Run: streamlit run dashboards/streamlit_dashboard.py
Requires: pip install streamlit requests plotly
"""

import time
import requests
import json
from datetime import datetime

try:
    import streamlit as st
    import plotly.graph_objects as go
    import plotly.express as px
    STREAMLIT_OK = True
except ImportError:
    STREAMLIT_OK = False
    print("Install: pip install streamlit plotly")

API_BASE = "http://localhost:8000/api"


def fetch(endpoint: str, fallback=None):
    """Fetch from the monitoring API with a fallback on error."""
    try:
        r = requests.get(f"{API_BASE}{endpoint}", timeout=4)
        r.raise_for_status()
        return r.json()
    except Exception:
        return fallback


def color_health(health: str) -> str:
    return {"excellent": "🟢", "good": "🔵", "degraded": "🟡", "critical": "🔴"}.get(health, "⚪")


def color_drift(status: str) -> str:
    return {"stable": "🟢", "warning": "🟡", "drifted": "🔴"}.get(status, "⚪")


def main():
    st.set_page_config(
        page_title="AI Monitoring Platform",
        page_icon="📡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("📡 AI System Monitoring Platform")
    st.caption(f"Live dashboard · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ── Sidebar ────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Controls")
        refresh_rate = st.selectbox("Auto-refresh", [5, 10, 30, 60], index=0)
        selected_model = st.selectbox(
            "Focus model",
            ["all", "fraud_detector_v1", "fraud_detector_v2",
             "recommendation_model", "vision_model", "nlp_sentiment"],
        )
        st.divider()
        st.header("🔗 API")
        st.code(f"GET {API_BASE}/health", language="bash")
        st.code(f"GET {API_BASE}/metrics/system", language="bash")
        if st.button("🔄 Refresh now"):
            st.rerun()
        st.divider()
        st.caption("Auto-refreshes every " + str(refresh_rate) + "s")

    # ── Health strip ───────────────────────────────────────────────────────
    health = fetch("/health") or {}
    alert_stats = fetch("/alerts/stats") or {}
    sys_metrics = fetch("/metrics/system") or {}
    app_metrics = fetch("/metrics/application") or {}

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Status", "✅ Healthy" if health.get("status") == "healthy" else "⚠️ " + health.get("status", "—"))
    col2.metric("CPU", f"{sys_metrics.get('cpu_percent', '—')}%")
    col3.metric("RAM", f"{sys_metrics.get('ram_percent', '—')}%")
    col4.metric("Avg latency", f"{app_metrics.get('avg_latency_ms', '—')}ms")
    col5.metric("Error rate", f"{app_metrics.get('error_rate_percent', '—')}%")
    col6.metric("Active alerts", alert_stats.get("active", "—"),
                delta=f"{alert_stats.get('critical', 0)} critical",
                delta_color="inverse")

    st.divider()

    # ── Tabs ───────────────────────────────────────────────────────────────
    tab_overview, tab_models, tab_latency, tab_drift, tab_anomalies, tab_alerts, tab_predict = st.tabs([
        "📊 Overview", "🤖 Models", "⏱ Latency", "📉 Drift",
        "🔍 Anomalies", "🔔 Alerts", "🔮 Predictions"
    ])

    # ── OVERVIEW ──────────────────────────────────────────────────────────
    with tab_overview:
        st.subheader("Throughput by model (last hour)")
        throughput = fetch("/metrics/throughput?minutes=60") or {}
        models_data = throughput.get("models", [])
        if models_data:
            fig = px.bar(
                models_data,
                x="model_id", y="total_requests",
                color="model_id",
                labels={"total_requests": "Requests", "model_id": "Model"},
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(showlegend=False, height=300, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("Error rate by model")
            err_data = fetch("/metrics/error-rate?minutes=60") or []
            if err_data:
                fig2 = px.bar(err_data, x="model_id", y="error_rate",
                              color="error_rate",
                              color_continuous_scale=["#1D9E75", "#BA7517", "#A32D2D"],
                              labels={"error_rate": "Error %", "model_id": "Model"})
                fig2.update_layout(height=260, margin=dict(t=10, b=10), showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

        with col_r:
            st.subheader("Latency timeseries (ms)")
            model_filter = None if selected_model == "all" else selected_model
            ts_url = "/metrics/latency/timeseries?minutes=60"
            if model_filter:
                ts_url += f"&model_id={model_filter}"
            ts = fetch(ts_url) or []
            if ts:
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=[r["bucket"] for r in ts],
                    y=[r["avg_latency"] for r in ts],
                    mode="lines", name="avg", line=dict(color="#1D9E75", width=2)
                ))
                fig3.add_trace(go.Scatter(
                    x=[r["bucket"] for r in ts],
                    y=[r["max_latency"] for r in ts],
                    mode="lines", name="max", line=dict(color="#A32D2D", width=1, dash="dot")
                ))
                fig3.update_layout(height=260, margin=dict(t=10, b=10),
                                   legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig3, use_container_width=True)

    # ── MODELS ───────────────────────────────────────────────────────────
    with tab_models:
        models_resp = fetch("/models") or {}
        models_list = models_resp.get("models", [])
        st.subheader(f"Registered models ({len(models_list)})")

        for m in models_list:
            stats = m.get("stats_1h", {})
            err = stats.get("error_rate") or 0
            lat = stats.get("avg_latency") or 0
            reqs = stats.get("requests_1h") or 0
            status_icon = "✅" if m["status"] == "active" else "🗑️"
            health_icon = "🔴" if err > 5 else "🟡" if err > 3 else "🟢"

            with st.expander(f"{status_icon} {m['model_id']} · {m['version']} {health_icon}"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Requests/hr", reqs)
                c2.metric("Avg latency", f"{lat:.0f}ms" if lat else "—")
                c3.metric("Error rate", f"{err:.1f}%" if err else "0%")
                c4.metric("Status", m["status"])
                if m.get("description"):
                    st.caption(m["description"])
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button(f"Full health report", key=f"health_{m['model_id']}"):
                        hdata = fetch(f"/models/{m['model_id']}/health") or {}
                        st.json(hdata)
                with col_b:
                    if st.button(f"Drift report", key=f"drift_{m['model_id']}"):
                        ddata = fetch(f"/drift/{m['model_id']}/report") or {}
                        st.json(ddata)

    # ── LATENCY ──────────────────────────────────────────────────────────
    with tab_latency:
        model_filter = None if selected_model == "all" else selected_model
        url = "/metrics/latency?minutes=60"
        if model_filter:
            url += f"&model_id={model_filter}"
        lat_stats = fetch(url) or {}

        if "avg_ms" in lat_stats:
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Avg", f"{lat_stats['avg_ms']}ms")
            c2.metric("P50", f"{lat_stats['p50_ms']}ms")
            c3.metric("P95", f"{lat_stats['p95_ms']}ms")
            c4.metric("P99", f"{lat_stats['p99_ms']}ms")
            c5.metric("Health", color_health(lat_stats.get("health", "")))

            st.subheader("Percentile breakdown")
            fig = go.Figure(go.Bar(
                x=["avg", "P50", "P95", "P99"],
                y=[lat_stats["avg_ms"], lat_stats["p50_ms"],
                   lat_stats["p95_ms"], lat_stats["p99_ms"]],
                marker_color=["#1D9E75", "#1D9E75", "#BA7517", "#A32D2D"],
                text=[f"{v}ms" for v in [lat_stats["avg_ms"], lat_stats["p50_ms"],
                                          lat_stats["p95_ms"], lat_stats["p99_ms"]]],
                textposition="outside",
            ))
            fig.update_layout(height=300, margin=dict(t=10, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Slow & critical requests"):
                st.metric("Slow requests (>300ms)", lat_stats.get("slow_requests", 0))
                st.metric("Critical requests (>2000ms)", lat_stats.get("critical_requests", 0))
        else:
            st.info("No latency data yet — traffic is being generated.")

    # ── DRIFT ─────────────────────────────────────────────────────────────
    with tab_drift:
        st.subheader("Drift analysis by model")
        drift_models = ["fraud_detector_v1", "fraud_detector_v2",
                        "recommendation_model", "vision_model", "nlp_sentiment"]
        drift_rows = []
        for mid in drift_models:
            d = fetch(f"/drift/{mid}/report") or {}
            conf = d.get("confidence_drift", {})
            lat = d.get("latency_drift", {})
            drift_rows.append({
                "Model": mid,
                "Conf drift": round(conf.get("drift_score", 0), 4),
                "Lat drift (PSI)": round(lat.get("psi_score", 0), 4),
                "Status": d.get("overall_status", "—"),
            })

        if drift_rows:
            for row in drift_rows:
                icon = color_drift(row["Status"])
                with st.expander(f"{icon} {row['Model']} — {row['Status']}"):
                    c1, c2 = st.columns(2)
                    c1.metric("Confidence drift", row["Conf drift"],
                              delta="⚠️ drifted" if row["Conf drift"] > 0.1 else "stable",
                              delta_color="inverse" if row["Conf drift"] > 0.1 else "off")
                    c2.metric("Latency drift (PSI)", row["Lat drift (PSI)"],
                              delta="⚠️ drifted" if row["Lat drift (PSI)"] > 0.2 else "stable",
                              delta_color="inverse" if row["Lat drift (PSI)"] > 0.2 else "off")

    # ── ANOMALIES ────────────────────────────────────────────────────────
    with tab_anomalies:
        summary = fetch("/metrics/anomalies") or {}
        st.metric("Anomalies detected (24h)", summary.get("total_last_24h", 0))
        by_type = summary.get("by_type", [])
        if by_type:
            fig = px.pie(by_type, names="anomaly_type", values="count",
                         title="Anomalies by type",
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(height=300, margin=dict(t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Recent anomalies")
        recent = summary.get("recent", [])
        if recent:
            for a in recent[:10]:
                st.markdown(f"**{a['anomaly_type']}** · `{a.get('model_id','—')}` · score `{a['score']}` · {a['timestamp']}")
        else:
            st.info("No anomalies detected yet.")

    # ── ALERTS ───────────────────────────────────────────────────────────
    with tab_alerts:
        active = fetch("/alerts/active") or {}
        alert_list = active.get("alerts", [])
        st.subheader(f"Active alerts ({len(alert_list)})")
        if alert_list:
            for a in alert_list:
                icon = "🔴" if a["severity"] == "critical" else "🟡"
                with st.expander(f"{icon} [{a['severity'].upper()}] {a['message'][:80]}"):
                    st.write(f"**Type:** {a['alert_type']}")
                    st.write(f"**Model:** {a.get('model_id', '—')}")
                    st.write(f"**Time:** {a['timestamp']}")
                    if st.button("✅ Resolve", key=f"resolve_{a['id']}"):
                        try:
                            requests.post(f"{API_BASE}/alerts/{a['id']}/resolve", timeout=4)
                            st.success("Resolved")
                            st.rerun()
                        except Exception:
                            st.error("Could not resolve alert")
        else:
            st.success("✅ No active alerts")

    # ── PREDICTIONS ──────────────────────────────────────────────────────
    with tab_predict:
        st.subheader("🔮 AI Failure Prediction (next 15 min)")
        st.caption("Linear trend analysis — flags models likely to breach thresholds soon.")
        preds = fetch("/advanced/predict") or {}
        for p in preds.get("predictions", []):
            risk = p.get("risk_level", "low")
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk, "⚪")
            with st.expander(f"{icon} {p['model_id']} — risk: {risk} (score: {p.get('risk_score', 0)})"):
                st.write(p.get("recommendation", ""))
                for pred in p.get("predictions", []):
                    st.metric(
                        pred["metric"],
                        f"current: {pred['current']}",
                        delta=f"→ {pred['projected']} projected",
                        delta_color="inverse",
                    )

    # ── Auto refresh ──────────────────────────────────────────────────────
    time.sleep(refresh_rate)
    st.rerun()


if __name__ == "__main__":
    main()
