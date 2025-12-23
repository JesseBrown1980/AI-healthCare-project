"""Streamlit page for model explainability using SHAP values."""

import os
from typing import Any, Dict, Optional

import pandas as pd
import requests
import streamlit as st
import altair as alt
from frontend.utils.env_loader import load_environment, get_api_url

load_environment()  # BEGIN AI GENERATED: centralized env loading # END AI GENERATED

API_URL = get_api_url()


@st.cache_data(ttl=30)
def fetch_explanation(patient_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve SHAP explanation payload from the backend."""

    try:
        response = requests.get(
            f"{API_URL}/patient/{patient_id}/explain",
            headers={"Accept": "application/json"},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # pragma: no cover - UI warning only
        st.warning(f"Could not fetch explanation: {exc}")
        return None


def render_shap_bars(feature_names: list[str], shap_values: list[float]):
    """Render a bar chart of the top SHAP contributors."""

    if not feature_names or not shap_values:
        st.info("No SHAP values available for this patient.")
        return

    df = pd.DataFrame(
        {
            "feature": feature_names,
            "shap_value": shap_values,
        }
    )
    df["magnitude"] = df["shap_value"].abs()
    top_features = df.sort_values("magnitude", ascending=False).head(10)

    chart = (
        alt.Chart(top_features)
        .mark_bar()
        .encode(
            x=alt.X("shap_value:Q", title="SHAP contribution"),
            y=alt.Y("feature:N", sort=list(reversed(top_features["feature"].tolist()))),
            color=alt.condition(alt.datum.shap_value > 0, alt.value("#dc2626"), alt.value("#16a34a")),
        )
    )

    st.altair_chart(chart, use_container_width=True)


def render_explainability():
    st.set_page_config(page_title="Explainability", page_icon="🧠", layout="wide")

    st.title("🧠 Model Explainability")
    st.caption("Inspect per-feature SHAP contributions for the baseline risk model.")

    col_left, col_right = st.columns([2, 1])
    with col_left:
        patient_id = st.text_input("Patient ID", value="demo-patient-1", help="FHIR patient identifier")
    with col_right:
        st.markdown(
            """
            The explainability view uses a lightweight logistic regression model trained on synthetic data.
            It highlights which structured features increase or decrease the baseline risk score.
            """
        )

    if not patient_id:
        st.info("Enter a patient ID to fetch SHAP values.")
        return

    explanation = fetch_explanation(patient_id)
    if not explanation:
        return

    st.markdown("---")
    top_row = st.columns(3)
    top_row[0].metric("Patient", patient_id)
    top_row[1].metric("Risk Score", f"{explanation.get('risk_score', 0):.2f}")
    top_row[2].metric("Model", explanation.get("model_type", "baseline"))

    render_shap_bars(explanation.get("feature_names", []), explanation.get("shap_values", []))

    with st.expander("Raw explanation payload"):
        st.json(explanation)


if __name__ == "__main__":
    render_explainability()
