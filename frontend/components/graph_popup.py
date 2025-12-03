"""
Graph Visualization Popup Component
Shows patient clinical graph in a modal/popup after analysis
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
from typing import Dict, Any, Optional, List


def render_graph_popup(
    patient_id: str,
    graph_data: Dict[str, Any],
    show_popup: bool = True,
    key: str = "graph_popup"
) -> bool:
    """
    Render a graph visualization popup/modal.
    
    Args:
        patient_id: Patient ID
        graph_data: Graph data from API (nodes, edges, statistics, anomaly_detection)
        show_popup: Whether to show the popup
        key: Unique key for the popup state
    
    Returns:
        True if popup should be shown, False otherwise
    """
    if not show_popup or not graph_data:
        return False
    
    # Initialize popup state
    if f"{key}_open" not in st.session_state:
        st.session_state[f"{key}_open"] = True
    
    # Close button state
    if f"{key}_closed" not in st.session_state:
        st.session_state[f"{key}_closed"] = False
    
    # If closed, don't show
    if st.session_state[f"{key}_closed"]:
        return False
    
    # Create modal-like container
    with st.container():
        # Header with close button
        col_header, col_close = st.columns([10, 1])
        with col_header:
            st.markdown("### 🕸️ Clinical Graph Visualization")
        with col_close:
            if st.button("✕", key=f"{key}_close_btn", help="Close"):
                st.session_state[f"{key}_closed"] = True
                st.rerun()
        
        st.markdown("---")
        
        # Extract graph components
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        stats = graph_data.get("statistics", {})
        anomaly_info = graph_data.get("anomaly_detection", {})
        
        if not nodes:
            st.info("No graph data available for this patient")
            return True
        
        # Display quick stats
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        with col_stat1:
            st.metric("Nodes", stats.get("total_nodes", 0))
        with col_stat2:
            st.metric("Edges", stats.get("total_edges", 0))
        with col_stat3:
            anomaly_count = anomaly_info.get("anomaly_count", 0) if anomaly_info else 0
            st.metric("Anomalies", anomaly_count, delta="Detected" if anomaly_count > 0 else None)
        with col_stat4:
            st.metric("Node Types", len(set(n.get("type", "unknown") for n in nodes)))
        
        st.markdown("---")
        
        # Create interactive network graph
        fig = create_network_graph(nodes, edges, anomaly_info)
        st.plotly_chart(fig, use_container_width=True, height=500)
        
        # Show anomaly details if available
        if anomaly_info and anomaly_info.get("anomaly_count", 0) > 0:
            with st.expander("🔍 Anomaly Details", expanded=False):
                anomalies = anomaly_info.get("anomalies", [])
                for i, anomaly in enumerate(anomalies[:5], 1):  # Show first 5
                    anomaly_type = anomaly.get("anomaly_type", "unknown")
                    score = anomaly.get("anomaly_score", 0.0)
                    severity = anomaly.get("severity", "low")
                    
                    severity_colors = {
                        "low": "🟡",
                        "medium": "🟠",
                        "high": "🔴",
                        "critical": "⛔"
                    }
                    
                    st.markdown(
                        f"**{i}. {anomaly_type.replace('_', ' ').title()}** "
                        f"{severity_colors.get(severity, '⚪')} "
                        f"Score: {score:.2f}"
                    )
                    if anomaly.get("description"):
                        st.caption(anomaly.get("description"))
        
        st.markdown("---")
        st.caption("💡 This graph shows clinical relationships detected by the GNN anomaly detection system")
    
    return True


def create_network_graph(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    anomaly_info: Optional[Dict[str, Any]] = None
) -> go.Figure:
    """
    Create an interactive network graph visualization using Plotly.
    
    Args:
        nodes: List of node dictionaries with id, label, type, color, etc.
        edges: List of edge dictionaries with source, target, type, etc.
        anomaly_info: Optional anomaly detection information
    
    Returns:
        Plotly figure object
    """
    if not nodes:
        # Return empty graph
        fig = go.Figure()
        fig.add_annotation(
            text="No graph data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig.update_layout(
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False),
            height=400
        )
        return fig
    
    # Create anomaly map for edge coloring
    anomaly_map = {}
    if anomaly_info:
        for anomaly in anomaly_info.get("anomalies", []):
            edge_idx = anomaly.get("edge_index")
            if edge_idx is not None:
                anomaly_map[edge_idx] = {
                    "score": anomaly.get("anomaly_score", 0.0),
                    "severity": anomaly.get("severity", "low")
                }
    
    # Use a force-directed layout (simplified spring layout)
    num_nodes = len(nodes)
    if num_nodes == 1:
        # Single node - center it
        node_positions = {nodes[0]["id"]: (0, 0)}
    else:
        # Circular layout as base, then add some randomness
        angles = np.linspace(0, 2 * np.pi, num_nodes, endpoint=False)
        radius = 3
        node_positions = {}
        for i, node in enumerate(nodes):
            angle = angles[i]
            # Add small random offset for better visualization
            offset = np.random.uniform(-0.3, 0.3, 2)
            x = radius * np.cos(angle) + offset[0]
            y = radius * np.sin(angle) + offset[1]
            node_positions[node["id"]] = (x, y)
    
    # Extract node positions
    node_x = [node_positions[node["id"]][0] for node in nodes]
    node_y = [node_positions[node["id"]][1] for node in nodes]
    node_text = [node.get("label", node["id"]) for node in nodes]
    node_colors = [node.get("color", "#CCCCCC") for node in nodes]
    node_sizes = [node.get("size", 15) for node in nodes]
    node_types = [node.get("type", "unknown") for node in nodes]
    
    # Create edge traces
    edge_x = []
    edge_y = []
    edge_colors = []
    edge_widths = []
    edge_hovertexts = []
    
    for i, edge in enumerate(edges):
        source_id = edge.get("source")
        target_id = edge.get("target")
        
        if source_id in node_positions and target_id in node_positions:
            x0, y0 = node_positions[source_id]
            x1, y1 = node_positions[target_id]
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            # Color based on anomaly
            edge_type = edge.get("type", "normal")
            if i in anomaly_map:
                anomaly = anomaly_map[i]
                if anomaly["severity"] == "critical":
                    color = "#FF0000"  # Red
                    width = 3
                elif anomaly["severity"] == "high":
                    color = "#FF6600"  # Orange
                    width = 2.5
                elif anomaly["severity"] == "medium":
                    color = "#FFAA00"  # Yellow-orange
                    width = 2
                else:
                    color = "#FFD700"  # Gold
                    width = 1.5
                hovertext = f"{edge_type}<br>Anomaly Score: {anomaly['score']:.2f}<br>Severity: {anomaly['severity']}"
            else:
                color = edge.get("color", "#CCCCCC")
                width = 1
                hovertext = edge_type
            
            edge_colors.append(color)
            edge_widths.append(width)
            edge_hovertexts.append(hovertext)
    
    # Create edge trace
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1, color="#CCCCCC"),
        hoverinfo="none",
        mode="lines",
        showlegend=False
    )
    
    # Create node trace
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="middle center",
        textfont=dict(size=10, color="white"),
        hovertext=[f"Type: {nt}<br>ID: {nid}" for nt, nid in zip(node_types, [n["id"] for n in nodes])],
        hoverinfo="text",
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color="white"),
            showscale=False
        ),
        showlegend=False
    )
    
    # Create figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=dict(
                text="Clinical Relationship Graph",
                font=dict(size=16),
                x=0.5,
                xanchor="center"
            ),
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=20, r=20, t=40),
            annotations=[
                dict(
                    text="Node colors: Blue=Patient, Red=Medication, Orange=Condition, Green=Provider, Purple=Lab Value",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=-0.1,
                    xanchor="center",
                    yanchor="top",
                    font=dict(size=10, color="#666666")
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="white",
            height=500
        )
    )
    
    return fig

