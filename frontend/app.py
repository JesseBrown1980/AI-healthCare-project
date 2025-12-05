"""
Frontend Streamlit Application
Interactive dashboard for healthcare AI assistant
"""

import streamlit as st
import requests
import json
from datetime import datetime
from typing import Optional, Dict, Any
import plotly.graph_objects as go
import plotly.express as px

# Configuration
API_URL = "http://localhost:8000/api/v1"
st.set_page_config(
    page_title="Healthcare AI Assistant",
    page_icon="🩺",  # Update to a base64 data URI for custom PNG if desired
    layout="wide",
    initial_sidebar_state="expanded"
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

def make_api_call(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Optional[Dict]:
    """Make API call to backend"""
    try:
        url = f"{API_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            return None
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None


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


def page_patient_analysis():
    """Patient analysis page"""
    st.title("🔬 Patient Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        patient_id = st.text_input(
            "Enter Patient ID (FHIR)",
            placeholder="patient-12345"
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
    
    patient_id = st.text_input(
        "Patient ID (optional for context)",
        placeholder="Leave empty for general query"
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
            with st.spinner("Processing feedback..."):
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
    
    # Sidebar navigation
    st.sidebar.title("🏥 Healthcare AI")
    page = st.sidebar.radio(
        "Navigation",
        [
            "Home",
            "Patient Analysis",
            "Medical Query",
            "Feedback",
            "Settings"
        ]
    )
    
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
    if page == "Home":
        page_home()
    elif page == "Patient Analysis":
        page_patient_analysis()
    elif page == "Medical Query":
        page_medical_query()
    elif page == "Feedback":
        page_feedback()
    elif page == "Settings":
        page_settings()


if __name__ == "__main__":
    main()
