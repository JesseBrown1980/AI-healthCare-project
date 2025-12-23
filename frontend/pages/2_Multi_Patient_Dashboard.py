import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st
from streamlit import st_autorefresh
from frontend.utils.env_loader import get_api_url, load_environment

load_environment()  # BEGIN AI GENERATED: centralized env loading # END AI GENERATED

API_URL = get_api_url()
REFRESH_INTERVAL_MS = int(os.getenv("DASHBOARD_REFRESH_MS", "20000"))


@st.cache_data(ttl=30)
def fetch_dashboard_patients() -> List[Dict[str, Any]]:
    """Fetch patient summaries for the multi-patient dashboard."""

    try:
        response = requests.get(f"{API_URL}/patients/dashboard", timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
    except Exception as exc:  # pragma: no cover - UI hint only
        st.warning(f"Could not fetch dashboard data: {exc}")

    # Fallback mock data
    now = datetime.utcnow().isoformat()
    return [
        {
            "patient_id": "demo-patient-1",
            "name": "Alex Johnson",
            "latest_risk_score": 0.72,
            "highest_alert_severity": "high",
            "last_analyzed_at": now,
        },
        {
            "patient_id": "demo-patient-2",
            "name": "Priya Singh",
            "latest_risk_score": 0.38,
            "highest_alert_severity": "medium",
            "last_analyzed_at": now,
        },
    ]


def parse_timestamp(raw_value: Any) -> Optional[datetime]:
    if raw_value is None:
        return None
    if isinstance(raw_value, datetime):
        return raw_value
    try:
        return datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
    except Exception:
        return None


def severity_badge(severity: str) -> str:
    colors = {
        "critical": "#fecdd3",
        "high": "#ffe4e6",
        "medium": "#fff7ed",
        "low": "#ecfeff",
        "none": "#ecfeff",
    }
    label = (severity or "none").title()
    color = colors.get(severity.lower() if severity else "none", "#f1f5f9")
    return f"<span style='background:{color};padding:4px 10px;border-radius:12px;font-weight:600;'>{label}</span>"


def render_dashboard():
    st.set_page_config(page_title="Multi-Patient Dashboard", page_icon="👥", layout="wide")

    st.title("👥 Multi-Patient Dashboard")
    st.caption("Overview of active patients with latest risk scores and alerts.")
    st_autorefresh(interval=REFRESH_INTERVAL_MS, key="dashboard_autorefresh")

    patients = fetch_dashboard_patients()
    if not patients:
        st.info("No patient data available.")
        return

    for patient in patients:
        patient["parsed_last_analyzed"] = parse_timestamp(patient.get("last_analyzed_at"))

    patients.sort(key=lambda p: (p.get("latest_risk_score") or 0), reverse=True)

    table_rows: List[Dict[str, Any]] = []
    for patient in patients:
        table_rows.append(
            {
                "Patient": f"{patient.get('name') or 'Unknown'} ({patient.get('patient_id')})",
                "Risk Score": patient.get("latest_risk_score"),
                "Alert Severity": patient.get("highest_alert_severity") or "none",
                "Last Analyzed": (
                    patient["parsed_last_analyzed"].strftime("%Y-%m-%d %H:%M")
                    if patient.get("parsed_last_analyzed")
                    else "Unknown"
                ),
            }
        )

    dataframe = pd.DataFrame(table_rows)

    def highlight_rows(row: pd.Series) -> List[str]:
        risk = row.get("Risk Score") or 0
        severity = str(row.get("Alert Severity", "none")).lower()
        if risk >= 0.75 or severity in {"high", "critical"}:
            return ["background-color: #fff1f2" for _ in row]
        return ["" for _ in row]

    styled = dataframe.style.apply(highlight_rows, axis=1).format({"Risk Score": "{:.2f}"})
    st.dataframe(styled, use_container_width=True, height=320)

    st.markdown("---")
    high_risk = [p for p in patients if (p.get("latest_risk_score") or 0) >= 0.75]
    if high_risk:
        st.subheader("🚨 High Risk Patients")
        for patient in high_risk:
            last_seen = patient.get("parsed_last_analyzed")
            st.write(
                f"**{patient.get('name') or patient.get('patient_id')}** — Risk Score: "
                f"{patient.get('latest_risk_score'):.2f} | Alerts: "
                f"{(patient.get('highest_alert_severity') or 'none').title()} | "
                f"Last analyzed: {last_seen.isoformat() if last_seen else 'unknown'}"
            )


if __name__ == "__main__":
    render_dashboard()
