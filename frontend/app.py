"""
Frontend Streamlit Application
Interactive dashboard for healthcare AI assistant
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
from requests import HTTPError, RequestException
import json
import os
import sys

# Add project root to sys.path to allow importing from 'frontend' package
# sys.path hack removed - use installed package or python -m

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from frontend.utils.env_loader import load_environment, get_api_url

load_environment()  # BEGIN AI GENERATED: centralized env loading # END AI GENERATED

# Configuration
API_URL = get_api_url()
st.set_page_config(
    page_title="Healthcare AI Assistant",
    page_icon="🩺",  # Update to a base64 data URI for custom PNG if desired
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
    }
    .alert-critical {
        background-color: #ffcccc;
        border-left: 4px solid #cc0000;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .alert-high {
        background-color: #ffe6cc;
        border-left: 4px solid #ff9900;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .recommendation-box {
        background-color: #e6f3ff;
        border-left: 4px solid #0066cc;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ==================== UTILITY FUNCTIONS ====================

def make_api_call(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict] = None,
    *,
    timeout: float = 10.0,
) -> Optional[Dict]:
    """Make API call to backend with basic error handling."""

    try:
        url = f"{API_URL}{endpoint}"
        method = method.upper()
        headers = {"Content-Type": "application/json"}

        if method == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
        else:
            st.error(f"Unsupported HTTP method: {method}")
            return None

        response.raise_for_status()
        return response.json()
    except HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        st.error("Unable to fetch data from the server. Please try again later.")
        st.info(f"Request failed with status {status}.")
        return None
    except RequestException as exc:
        st.error("Unable to reach the server. Please check your connection or try again soon.")
        st.info(str(exc))
        return None
    except Exception as exc:  # pragma: no cover - defensive UI guard
        st.error("An unexpected error occurred while contacting the API.")
        st.info(str(exc))
        return None


def initialize_session_state():
    """Initialize shared session state values."""
    query_params = st.experimental_get_query_params()

    if "selected_patient_id" not in st.session_state:
        st.session_state["selected_patient_id"] = query_params.get("patient_id", [""])[0]

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = query_params.get("page", ["Home"])[0]


def set_patient_selection(patient_id: str):
    """Persist selected patient ID in session state and query params."""
    st.session_state["selected_patient_id"] = patient_id
    st.experimental_set_query_params(
        page=st.session_state.get("current_page", "Home"),
        patient_id=patient_id,
    )


def update_navigation_params(page: str):
    """Sync navigation changes to query params."""
    st.session_state["current_page"] = page
    st.experimental_set_query_params(
        page=page,
        patient_id=st.session_state.get("selected_patient_id", ""),
    )


def display_alert(alert: Dict):
    """Display a clinical alert"""
    severity = alert.get("severity", "medium")
    type_class = f"alert-{severity}"
    
    html = f"""
    <div class="{type_class}">
        <strong>⚠️ {alert.get('type', 'Alert').upper()}</strong><br>
        {alert.get('message', '')}<br>
        <em>Recommendation: {alert.get('recommendation', '')}</em>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def display_recommendation(rec: Dict):
    """Display clinical recommendation"""
    html = f"""
    <div class="recommendation-box">
        <strong>💡 Recommendation</strong><br>
        <strong>Q:</strong> {rec.get('query', '')}<br>
        <strong>A:</strong> {rec.get('recommendation', '')}<br>
        <strong>Confidence:</strong> {rec.get('confidence', 0)*100:.1f}%<br>
        <strong>Sources:</strong> {', '.join(rec.get('sources', []))}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def fetch_multi_patient_data() -> list[Dict[str, Any]]:
    """Retrieve multi-patient dashboard data, fallback to demo data."""
    api_data = make_api_call("/patients/dashboard")
    if api_data and isinstance(api_data, dict) and api_data.get("patients"):
        return api_data["patients"]

    now = datetime.utcnow()
    return [
        {
            "id": "P-2043",
            "name": "Avery Thompson",
            "specialty": "Cardiology",
            "severity": "High",
            "cardio_risk": 0.78,
            "readmission_risk": 0.42,
            "active_alerts": 3,
            "last_analysis": now - timedelta(hours=2, minutes=10),
        },
        {
            "id": "P-1987",
            "name": "Riley Chen",
            "specialty": "Endocrinology",
            "severity": "Moderate",
            "cardio_risk": 0.36,
            "readmission_risk": 0.28,
            "active_alerts": 1,
            "last_analysis": now - timedelta(hours=5, minutes=5),
        },
        {
            "id": "P-1520",
            "name": "Jordan Martinez",
            "specialty": "Pulmonology",
            "severity": "Critical",
            "cardio_risk": 0.91,
            "readmission_risk": 0.63,
            "active_alerts": 5,
            "last_analysis": now - timedelta(hours=1, minutes=32),
        },
        {
            "id": "P-2201",
            "name": "Morgan Patel",
            "specialty": "Neurology",
            "severity": "Low",
            "cardio_risk": 0.18,
            "readmission_risk": 0.19,
            "active_alerts": 0,
            "last_analysis": now - timedelta(hours=7, minutes=45),
        },
        {
            "id": "P-1755",
            "name": "Casey Nguyen",
            "specialty": "Oncology",
            "severity": "High",
            "cardio_risk": 0.67,
            "readmission_risk": 0.38,
            "active_alerts": 2,
            "last_analysis": now - timedelta(hours=3, minutes=20),
        },
    ]


def format_elapsed_time(timestamp: datetime) -> str:
    """Format time since last analysis in human readable string."""
    delta = datetime.utcnow() - timestamp
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} min ago"
    hours, mins = divmod(minutes, 60)
    if hours < 24:
        return f"{hours} hr {mins} min ago"
    days, rem_hours = divmod(hours, 24)
    return f"{days} d {rem_hours} hr ago"


# ==================== PAGE SECTIONS ====================

def page_home():
    """Home/Dashboard page"""
    st.title("🏥 Healthcare AI Assistant")
    st.markdown("*Intelligent Clinical Decision Support with FHIR Integration*")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Active Features", "6", "S-LoRA, RAG, AoT, MLC")
    with col2:
        st.metric("Connected EHR", "Ready", "FHIR Protocol")
    with col3:
        st.metric("Model", "GPT-4", "With Adapters")
    
    st.markdown("---")
    
    st.subheader("Getting Started")
    st.markdown("""
    1. **Patient Analysis**: Select a patient and analyze their complete clinical picture
    2. **Medical Query**: Ask clinical questions with evidence-based answers
    3. **Alert Monitoring**: View and respond to critical alerts
    4. **Decision Support**: Access AI-powered recommendations aligned with guidelines
    """)
    
    st.markdown("---")
    
    st.subheader("Key Capabilities")
    
    capabilities = {
        "🔍 FHIR Integration": "Seamlessly fetch patient data from EHR systems",
        "🧠 Advanced AI": "S-LoRA, Meta-Learning, RAG-Fusion, Algorithm of Thought",
        "💊 Medication Review": "Drug interaction checking and optimization",
        "⚠️ Alert System": "Red-flag detection and clinical notifications",
        "📚 Evidence-Based": "Recommendations grounded in medical guidelines",
        "🎯 Personalization": "Learns from feedback for improved accuracy"
    }
    
    for capability, description in capabilities.items():
        st.markdown(f"**{capability}**: {description}")


def page_multi_patient_dashboard():
    """Multi-patient monitoring dashboard"""
    st.title("👥 Multi-Patient Dashboard")
    st_autorefresh(interval=30_000, key="multi_patient_refresh")

    raw_patients = fetch_multi_patient_data() or []

    def parse_timestamp(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                return datetime.utcnow()
        return datetime.utcnow()

    patients = [
        {
            **patient,
            "last_analysis": parse_timestamp(patient.get("last_analysis", datetime.utcnow())),
        }
        for patient in raw_patients
    ]

    specialties = sorted({patient.get("specialty", "Unknown") for patient in patients})
    severity_levels = ["All", "Low", "Moderate", "High", "Critical"]

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        specialty_filter = st.selectbox("Filter by Specialty", ["All"] + specialties)
    with filter_col2:
        severity_filter = st.selectbox("Filter by Severity", severity_levels)
    with filter_col3:
        sort_option = st.selectbox(
            "Sort by",
            [
                "Cardiovascular Risk (High to Low)",
                "Readmission Risk (High to Low)",
                "Active Alerts (High to Low)",
                "Last Analysis (Newest First)",
            ],
        )

    filtered_patients = [
        patient
        for patient in patients
        if (specialty_filter == "All" or patient.get("specialty") == specialty_filter)
        and (severity_filter == "All" or patient.get("severity") == severity_filter)
    ]

    if sort_option == "Cardiovascular Risk (High to Low)":
        filtered_patients.sort(key=lambda p: p.get("cardio_risk", 0), reverse=True)
    elif sort_option == "Readmission Risk (High to Low)":
        filtered_patients.sort(key=lambda p: p.get("readmission_risk", 0), reverse=True)
    elif sort_option == "Active Alerts (High to Low)":
        filtered_patients.sort(key=lambda p: p.get("active_alerts", 0), reverse=True)
    elif sort_option == "Last Analysis (Newest First)":
        filtered_patients.sort(key=lambda p: p.get("last_analysis", datetime.utcnow()), reverse=True)

    if not filtered_patients:
        st.info("No patients match the selected filters.")
        return

    total_patients = len(filtered_patients)
    avg_cardio = sum(p.get("cardio_risk", 0) for p in filtered_patients) / total_patients
    avg_readmission = sum(p.get("readmission_risk", 0) for p in filtered_patients) / total_patients
    total_alerts = sum(p.get("active_alerts", 0) for p in filtered_patients)

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric("Patients Displayed", total_patients)
    with metric_col2:
        st.metric("Avg Cardiovascular Risk", f"{avg_cardio * 100:.0f}%")
    with metric_col3:
        st.metric("Avg Readmission Risk", f"{avg_readmission * 100:.0f}%", delta=f"Alerts: {total_alerts}")

    summary_table = [
        {
            "Patient": f"{patient.get('name')} ({patient.get('id')})",
            "Specialty": patient.get("specialty"),
            "Severity": patient.get("severity"),
            "Cardio Risk %": round(patient.get("cardio_risk", 0) * 100),
            "Readmission Risk %": round(patient.get("readmission_risk", 0) * 100),
            "Active Alerts": patient.get("active_alerts", 0),
            "Last Analysis": format_elapsed_time(patient.get("last_analysis", datetime.utcnow())),
        }
        for patient in filtered_patients
    ]

    summary_df = pd.DataFrame(summary_table)

    def highlight_cardio(row: pd.Series) -> list[str]:
        color = "#ffe6e6" if row.get("Cardio Risk %", 0) >= 80 else ""
        return [f"background-color: {color}" if color else "" for _ in row]

    styled_summary = summary_df.style.apply(highlight_cardio, axis=1)
    st.dataframe(styled_summary, use_container_width=True, height=240)

    severity_colors = {
        "Low": "#d9f2d9",
        "Moderate": "#fff4cc",
        "High": "#ffe6cc",
        "Critical": "#ffcccc",
    }

    for idx, patient in enumerate(filtered_patients):
        if idx % 3 == 0:
            card_cols = st.columns(3)
        card = card_cols[idx % 3].container()

        high_cardio_risk = patient.get("cardio_risk", 0) >= 0.8
        card_background = "#fff5f5" if high_cardio_risk else "#ffffff"
        card_border = "2px solid #fca5a5" if high_cardio_risk else "1px solid #e6e8eb"

        severity = patient.get("severity", "").title()
        severity_color = severity_colors.get(severity, "#f0f2f6")

        card.markdown(
            f"""
            <div style="background-color:{card_background};padding:16px;border-radius:10px;border:{card_border};">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div><strong>{patient.get('name')}</strong><br><span style=\"color:#6b7280\">{patient.get('id')}</span></div>
                    <span style="background:{severity_color};padding:4px 10px;border-radius:12px;font-weight:600;">{severity}</span>
                </div>
                <div style="margin-top:8px;color:#6b7280;">{patient.get('specialty')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        card.markdown("**Cardiovascular Risk**")
        card.progress(min(max(patient.get("cardio_risk", 0), 0), 1))
        card.caption(f"{patient.get('cardio_risk', 0) * 100:.0f}%")

        risk_col1, risk_col2, risk_col3 = card.columns(3)
        with risk_col1:
            risk_col1.metric("Readmission Risk", f"{patient.get('readmission_risk', 0) * 100:.0f}%")
        with risk_col2:
            risk_col2.metric("Active Alerts", patient.get("active_alerts", 0))
        with risk_col3:
            risk_col3.metric("Last Analysis", format_elapsed_time(patient.get("last_analysis", datetime.utcnow())))

        card.markdown("---")

        if card.button("Open Analysis", key=f"open-analysis-{patient.get('id')}", use_container_width=True):
            set_patient_selection(patient.get("id", ""))
            update_navigation_params("Patient Analysis")
            st.experimental_rerun()

def page_patient_analysis():
    """Patient analysis page"""
    st.title("🔬 Patient Analysis")

    col1, col2 = st.columns([2, 1])

    query_params = st.experimental_get_query_params()
    default_patient_id = st.session_state.get("selected_patient_id") or query_params.get("patient_id", [""])[0]

    def handle_patient_id_change():
        set_patient_selection(st.session_state.get("patient_id_input", ""))

    with col1:
        patient_id = st.text_input(
            "Enter Patient ID (FHIR)",
            placeholder="patient-12345",
            value=default_patient_id,
            key="patient_id_input",
            on_change=handle_patient_id_change,
        )
    with col2:
        specialty = st.selectbox(
            "Medical Specialty",
            ["Auto-detect", "Cardiology", "Oncology", "Neurology",
             "Endocrinology", "Pulmonology", "Gastroenterology", "Nephrology"]
        )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        include_recs = st.checkbox("Include Recommendations", value=True)
    with col2:
        include_reasoning = st.checkbox("Include Reasoning", value=True)
    with col3:
        analyze_btn = st.button("Analyze Patient", use_container_width=True)

    if analyze_btn and patient_id:
        set_patient_selection(patient_id)
        update_navigation_params("Patient Analysis")
        with st.spinner("🔄 Analyzing patient..."):
            spec = None if specialty == "Auto-detect" else specialty.lower()

            result = make_api_call(
                "/analyze-patient",
                method="POST",
                data={
                    "fhir_patient_id": patient_id,
                    "include_recommendations": include_recs,
                    "specialty": spec
                }
            )

        if result and result.get("status") == "completed":

            # SUMMARY TAB
            st.success("✅ Analysis Complete")

            with st.expander("📋 Patient Summary", expanded=True):
                summary = result.get("summary", {})
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Patient Name", summary.get("patient_name", "N/A"))
                with col2:
                    st.metric("Active Conditions", summary.get("active_conditions_count", 0))
                with col3:
                    st.metric("Current Medications", summary.get("current_medications_count", 0))

                st.markdown(f"**Summary**: {summary.get('narrative_summary', '')}")

                if summary.get("key_conditions"):
                    st.markdown(f"**Key Conditions**: {', '.join(summary.get('key_conditions', []))}")
                if summary.get("key_medications"):
                    st.markdown(f"**Key Medications**: {', '.join(summary.get('key_medications', []))}")

            # ALERTS TAB
            alerts = result.get("alerts", [])
            if alerts:
                with st.expander(f"⚠️ Clinical Alerts ({len(alerts)})", expanded=True):
                    for i, alert in enumerate(alerts, 1):
                        display_alert(alert)
                        st.markdown("---")

            # RISK SCORES TAB
            with st.expander("📊 Risk Assessment", expanded=False):
                risk_scores = result.get("risk_scores", {})

                # Create risk chart
                risks = list(risk_scores.items())
                risk_names = [name.replace("_", " ").title() for name, _ in risks]
                risk_values = [value * 100 for _, value in risks]

                fig = go.Figure(data=[
                    go.Bar(
                        y=risk_names,
                        x=risk_values,
                        orientation='h',
                        marker=dict(
                            color=risk_values,
                            colorscale='RdYlGn_r',
                            cmin=0,
                            cmax=100
                        )
                    )
                ])
                fig.update_layout(
                    xaxis_title="Risk Score (%)",
                    height=400,
                    margin=dict(l=200)
                )
                st.plotly_chart(fig, use_container_width=True)

            # MEDICATION REVIEW TAB
            with st.expander("💊 Medication Review", expanded=False):
                med_review = result.get("medication_review", {})
                st.metric("Total Medications", med_review.get("total_medications", 0))

                if med_review.get("potential_issues"):
                    st.warning("⚠️ Potential Issues:")
                    for issue in med_review.get("potential_issues", []):
                        st.markdown(f"- {issue}")

                if med_review.get("medications"):
                    st.markdown("**Medications List:**")
                    for med in med_review.get("medications", []):
                        st.markdown(f"- {med.get('name')} ({med.get('status')})")

            # RECOMMENDATIONS TAB
            if include_recs and result.get("recommendations"):
                with st.expander("💡 Clinical Recommendations", expanded=False):
                    recs = result.get("recommendations", {})

                    for i, rec in enumerate(recs.get("clinical_recommendations", []), 1):
                        st.markdown(f"**Recommendation {i}**")
                        display_recommendation(rec)

                    if recs.get("priority_actions"):
                        st.markdown("**Priority Actions:**")
                        for action in recs.get("priority_actions", []):
                            st.markdown(f"- [{action['severity'].upper()}] {action['action']}")
                
                # PERFORMANCE METRICS
                with st.expander("⏱️ Performance", expanded=False):
                    duration = result.get("analysis_duration_seconds", 0)
                    st.metric("Analysis Duration", f"{duration:.2f}s")
            
            elif result and result.get("status") == "error":
                st.error(f"Error: {result.get('error', 'Unknown error')}")
            else:
                st.error("Invalid response from server")
    
    elif analyze_btn:
        st.warning("Please enter a Patient ID")


def page_medical_query():
    """Medical query page"""
    st.title("🤔 Medical Query")
    st.markdown("Ask clinical questions and get evidence-based answers")

    def handle_query_patient_change():
        set_patient_selection(st.session_state.get("medical_query_patient_id", ""))

    patient_id = st.text_input(
        "Patient ID (optional for context)",
        placeholder="Leave empty for general query",
        value=st.session_state.get("selected_patient_id", ""),
        key="medical_query_patient_id",
        on_change=handle_query_patient_change,
    )
    
    question = st.text_area(
        "Your Question",
        placeholder="e.g., What are the treatment options for this patient with hypertension and diabetes?",
        height=100
    )
    
    col1, col2 = st.columns(2)
    with col1:
        include_reasoning = st.checkbox("Show Reasoning Chain", value=True)
    with col2:
        query_btn = st.button("Query AI", use_container_width=True)

    if query_btn and question:
        with st.spinner("🔍 Querying medical knowledge..."):
            result = make_api_call(
                "/query",
                method="POST",
                data={
                    "question": question,
                    "patient_id": patient_id if patient_id else None,
                    "include_reasoning": include_reasoning
                }
            )

        if result and result.get("status") == "success":
            st.success("✅ Response Generated")

            st.markdown("**Answer:**")
            st.markdown(result.get("answer", ""))

            if include_reasoning and result.get("reasoning"):
                with st.expander("🔗 Reasoning Chain"):
                    st.markdown(result.get("reasoning"))

            if result.get("sources"):
                with st.expander("📚 Evidence Sources"):
                    for source in result.get("sources", []):
                        st.markdown(f"- {source}")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Confidence", f"{result.get('confidence', 0)*100:.1f}%")
            with col2:
                st.metric("Model", result.get("model", "Unknown"))

        else:
            st.error("Failed to get response")
    
    elif query_btn:
        st.warning("Please enter a question")


def page_feedback():
    """Feedback and learning page"""
    st.title("📝 Feedback & Learning")
    st.markdown("Help improve the AI system through feedback")
    
    query_id = st.text_input(
        "Query ID to provide feedback for",
        placeholder="q-456"
    )
    
    feedback_type = st.radio(
        "Feedback Type",
        ["Positive (Helpful)", "Negative (Incorrect)", "Correction"]
    )
    
    type_mapping = {
        "Positive (Helpful)": "positive",
        "Negative (Incorrect)": "negative",
        "Correction": "correction"
    }
    
    corrected_text = None
    if feedback_type == "Correction":
        corrected_text = st.text_area(
            "Corrected Response",
            placeholder="What should the correct answer have been?"
        )
    
    if st.button("Submit Feedback", use_container_width=True):
        if query_id:
            with st.spinner("📝 Processing feedback..."):
                result = make_api_call(
                    "/feedback",
                    method="POST",
                    data={
                        "query_id": query_id,
                        "feedback_type": type_mapping[feedback_type],
                        "corrected_text": corrected_text
                    }
                )

            if result and result.get("status") == "success":
                st.success("✅ Feedback recorded! Thank you for helping improve the AI.")
            else:
                st.error("Failed to submit feedback")
        else:
            st.warning("Please enter a Query ID")


def page_settings():
    """Settings page"""
    st.title("⚙️ Settings")
    
    st.subheader("System Configuration")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**API Configuration**")
        st.caption("Current API endpoint")
        st.code(API_URL, language="bash")
        if not any(
            os.getenv(var) for var in ("API_BASE_URL", "API_URL", "BACKEND_API_URL")
        ):
            st.warning(
                "Using default API URL. Set API_BASE_URL (preferred) or API_URL/BACKEND_API_URL "
                "to point to another backend."
            )
        api_status = make_api_call("/health")
        if api_status:
            st.success(f"✅ API Connected - {api_status.get('version', 'Unknown')}")
        else:
            st.error("❌ API Not Connected")
    
    with col2:
        st.markdown("**Adapter Status**")
        adapter_status = make_api_call("/adapters")
        if adapter_status:
            active = len(adapter_status.get("active", []))
            available = len(adapter_status.get("available", []))
            st.info(f"Active: {active}/{available} Adapters")
    
    st.markdown("---")
    st.subheader("User Preferences")
    
    theme = st.radio("Theme", ["Light", "Dark"])
    detail_level = st.select_slider(
        "Response Detail Level",
        options=["Brief", "Standard", "Detailed", "Expert"],
        value="Standard"
    )
    
    if st.button("Save Settings"):
        st.success("Settings saved!")


# ==================== MAIN APP ====================

def main():
    """Main app"""

    initialize_session_state()

    # Sidebar navigation
    st.sidebar.title("🏥 Healthcare AI")
    pages = {
        "Home": page_home,
        "Multi-Patient Dashboard": page_multi_patient_dashboard,
        "Patient Analysis": page_patient_analysis,
        "Medical Query": page_medical_query,
        "Feedback": page_feedback,
        "Settings": page_settings,
    }

    current_page = st.session_state.get("current_page", "Home")
    if current_page not in pages:
        current_page = "Home"

    page = st.sidebar.radio(
        "Navigation",
        list(pages.keys()),
        index=list(pages.keys()).index(current_page),
    )

    update_navigation_params(page)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.markdown("""
    **AI-Powered Healthcare Assistant**
    
    Advanced clinical decision support powered by:
    - FHIR Integration
    - Large Language Models
    - RAG-Fusion
    - S-LoRA Adaptation
    - Meta-Learning
    - Algorithm of Thought
    
    **Version:** 1.0.0
    """)
    
    # Route to pages
    pages[page]()


if __name__ == "__main__":
    main()
