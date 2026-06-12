"""
=============================================================================
  AI TRANSFORMER HEALTH MONITORING SYSTEM — Email Notification Service
  RPPL Transformers · SMTP integration & Alert cooldown
=============================================================================
"""

import os
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Retrieve database helpers for cooldown checks
from database.mongodb import get_last_alert_time

# SMTP Settings from environment variables
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_DEFAULT_SENDER = os.environ.get("SMTP_DEFAULT_SENDER", "alerts@rpplmonitoring.com")
ALERT_RECIPIENT_EMAIL = os.environ.get("ALERT_RECIPIENT_EMAIL", "")

def send_fault_alert_email(transformer_id, location, service_station, latitude, longitude, 
                           predicted_health, fault_type, fault_severity, fault_priority, 
                           health_score, maintenance_status, device_timestamp):
    """
    Sends an SMTP email alert for a Critical transformer status, enforcing a 30-minute 
    cooldown per transformer ID to prevent duplicate messages.
    """
    current_time = datetime.datetime.now()
    
    # ── Cooldown Check ────────────────────────────────────────────────────────
    last_alert = get_last_alert_time(transformer_id)
    if last_alert:
        # last_alert is a datetime object
        elapsed_minutes = (current_time - last_alert).total_seconds() / 60.0
        if elapsed_minutes < 30.0:
            print(f"[EMAIL] Skipping alert email for {transformer_id}: Cooldown active ({elapsed_minutes:.1f}m elapsed, threshold is 30m).")
            return False

    # ── Prepare Email Body ───────────────────────────────────────────────────
    maps_link = f"https://maps.google.com/?q={latitude},{longitude}"
    
    subject = "⚠ Critical Transformer Fault Alert"
    
    body = f"""Transformer Fault Detected

Transformer ID: {transformer_id}
Location: {location}
Service Station: {service_station}
Health Score: {health_score}%
Health Status: {predicted_health}
Fault Type: {fault_type}
Fault Severity: {fault_severity}
Fault Priority: {fault_priority}
Maintenance Status: {maintenance_status}
Timestamp: {device_timestamp}
Latitude: {latitude}
Longitude: {longitude}

Google Maps Link:
{maps_link}

Immediate inspection required.
"""

    # ── Dev Fallback Check ────────────────────────────────────────────────────
    # If SMTP settings are not provided, print alert to console & logs and return True (simulated success)
    if not SMTP_USER or not SMTP_PASSWORD or not ALERT_RECIPIENT_EMAIL:
        print("\n" + "="*70)
        print("  [ALERT SIMULATION] CRITICAL FAULT EMAIL ALERT TRIGGERED")
        print("="*70)
        print(f"  Subject: {subject}")
        print(f"  To     : {ALERT_RECIPIENT_EMAIL or '[NOT CONFIGURED - log fallback]'}")
        print("-"*70)
        print(body)
        print("="*70 + "\n")
        return True

    # ── Send Real Email ──────────────────────────────────────────────────────
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_DEFAULT_SENDER
        msg['To'] = ALERT_RECIPIENT_EMAIL
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_DEFAULT_SENDER, [ALERT_RECIPIENT_EMAIL], msg.as_string())
        server.quit()
        
        print(f"[EMAIL] Alert email dispatched successfully for {transformer_id} to {ALERT_RECIPIENT_EMAIL}.")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send email alert for {transformer_id}: {e}")
        # Return True for simulation robustness in case of transient local network issues, 
        # but print warning
        return False
