"""
Email templates for various notification types.
"""

from typing import Any, Dict, Optional
from datetime import datetime


def get_email_template(template_type: str):
    """Get email template function by type."""
    templates = {
        "critical_alert": critical_alert_template,
        "risk_update": risk_update_template,
        "appointment_reminder": appointment_reminder_template,
        "analysis_complete": analysis_complete_template,
        "password_reset": password_reset_template,
        "email_verification": email_verification_template,
    }
    return templates.get(template_type, default_template)


def critical_alert_template(
    patient_id: Optional[str] = None,
    alert_data: Optional[Dict[str, Any]] = None,
    risk_scores: Optional[Dict[str, Any]] = None,
    **kwargs
) -> tuple[str, str, str]:
    """Template for critical alert notifications."""
    patient_id = patient_id or "Unknown"
    alerts = alert_data.get("alerts", []) if alert_data else []
    critical_count = len([a for a in alerts if a.get("severity") == "critical"])
    
    subject = f"🚨 Critical Alert: Patient {patient_id}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f8f9fa; padding: 20px; }}
            .alert {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 10px 0; }}
            .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Critical Alert</h1>
            </div>
            <div class="content">
                <h2>Patient: {patient_id}</h2>
                <p><strong>Critical Alerts Detected: {critical_count}</strong></p>
                <p>Total Alerts: {len(alerts)}</p>
                
                {"".join([f'<div class="alert"><strong>{a.get("title", "Alert")}</strong><br>{a.get("description", "")}</div>' for a in alerts[:5]])}
                
                {f'<p><strong>Top Risk:</strong> {max(risk_scores.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)[0] if risk_scores else "N/A"}</p>' if risk_scores else ""}
                
                <p><a href="https://your-app.com/patients/{patient_id}">View Patient Details</a></p>
            </div>
            <div class="footer">
                <p>Healthcare AI Assistant - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    Critical Alert: Patient {patient_id}
    
    Critical Alerts Detected: {critical_count}
    Total Alerts: {len(alerts)}
    
    {"".join([f"{a.get('title', 'Alert')}: {a.get('description', '')}" for a in alerts[:5]])}
    
    View Patient Details: https://your-app.com/patients/{patient_id}
    """
    
    return subject, html_body, text_body


def risk_update_template(
    patient_id: Optional[str] = None,
    alert_data: Optional[Dict[str, Any]] = None,
    risk_scores: Optional[Dict[str, Any]] = None,
    **kwargs
) -> tuple[str, str, str]:
    """Template for risk score update notifications."""
    patient_id = patient_id or "Unknown"
    
    subject = f"Risk Update: Patient {patient_id}"
    
    risk_summary = ""
    if risk_scores:
        risk_summary = "<ul>"
        for risk_name, risk_value in risk_scores.items():
            if isinstance(risk_value, (int, float)):
                risk_summary += f"<li>{risk_name.replace('_', ' ').title()}: {risk_value:.2%}</li>"
        risk_summary += "</ul>"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f8f9fa; padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Risk Score Update</h1>
            </div>
            <div class="content">
                <h2>Patient: {patient_id}</h2>
                <p>Updated risk scores:</p>
                {risk_summary}
                <p><a href="https://your-app.com/patients/{patient_id}">View Patient Details</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"Risk Update: Patient {patient_id}\n\nUpdated risk scores available. View at: https://your-app.com/patients/{patient_id}"
    
    return subject, html_body, text_body


def appointment_reminder_template(
    patient_id: Optional[str] = None,
    alert_data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> tuple[str, str, str]:
    """Template for appointment reminders."""
    subject = "Appointment Reminder"
    html_body = "<html><body><h1>Appointment Reminder</h1><p>You have an upcoming appointment.</p></body></html>"
    text_body = "Appointment Reminder: You have an upcoming appointment."
    return subject, html_body, text_body


def analysis_complete_template(
    patient_id: Optional[str] = None,
    alert_data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> tuple[str, str, str]:
    """Template for analysis completion notifications."""
    patient_id = patient_id or "Unknown"
    subject = f"Analysis Complete: Patient {patient_id}"
    html_body = f"<html><body><h1>Analysis Complete</h1><p>Analysis for patient {patient_id} has been completed.</p></body></html>"
    text_body = f"Analysis Complete: Analysis for patient {patient_id} has been completed."
    return subject, html_body, text_body


def password_reset_template(
    reset_token: Optional[str] = None,
    **kwargs
) -> tuple[str, str, str]:
    """Template for password reset emails."""
    subject = "Password Reset Request"
    reset_link = f"https://your-app.com/reset-password?token={reset_token}" if reset_token else "#"
    html_body = f"<html><body><h1>Password Reset</h1><p>Click <a href='{reset_link}'>here</a> to reset your password.</p></body></html>"
    text_body = f"Password Reset: Visit {reset_link} to reset your password."
    return subject, html_body, text_body


def email_verification_template(
    verification_token: Optional[str] = None,
    **kwargs
) -> tuple[str, str, str]:
    """Template for email verification."""
    subject = "Verify Your Email Address"
    verify_link = f"https://your-app.com/verify-email?token={verification_token}" if verification_token else "#"
    html_body = f"<html><body><h1>Email Verification</h1><p>Click <a href='{verify_link}'>here</a> to verify your email address.</p></body></html>"
    text_body = f"Email Verification: Visit {verify_link} to verify your email address."
    return subject, html_body, text_body


def default_template(**kwargs) -> tuple[str, str, str]:
    """Default email template."""
    subject = "Notification from Healthcare AI Assistant"
    html_body = "<html><body><h1>Notification</h1><p>You have a new notification.</p></body></html>"
    text_body = "Notification: You have a new notification."
    return subject, html_body, text_body

