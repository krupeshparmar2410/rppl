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
from utils.logger import get_logger

logger = get_logger("email_service")

# SMTP Settings from environment variables (Task 7 + backward compatibility)
SMTP_SERVER = os.environ.get("MAIL_SERVER") or os.environ.get("SMTP_SERVER") or "smtp.gmail.com"
SMTP_PORT_RAW = os.environ.get("MAIL_PORT") or os.environ.get("SMTP_PORT") or "587"
try:
    SMTP_PORT = int(SMTP_PORT_RAW)
except ValueError:
    SMTP_PORT = 587

SMTP_USER = os.environ.get("MAIL_USERNAME") or os.environ.get("SMTP_USER") or ""
SMTP_PASSWORD = os.environ.get("MAIL_PASSWORD") or os.environ.get("SMTP_PASSWORD") or ""
SMTP_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or os.environ.get("SMTP_DEFAULT_SENDER") or "alerts@rpplmonitoring.com"
ALERT_RECIPIENT_EMAIL = os.environ.get("MAIL_RECIPIENT") or os.environ.get("ALERT_RECIPIENT_EMAIL") or ""

def send_fault_alert_email(transformer_id, city, service_station, latitude, longitude, 
                           predicted_health, fault_type, fault_severity, fault_priority, 
                           health_score, maintenance_status, device_timestamp,
                           nearest_service_station=None, distance_km=None):
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
            logger.info(f"Skipping alert email for {transformer_id}: Cooldown active ({elapsed_minutes:.1f}m elapsed, threshold is 30m).")
            return False

    # ── Prepare Email Body ───────────────────────────────────────────────────
    maps_link = f"https://maps.google.com/?q={latitude},{longitude}"
    
    subject = f"⚠ Transformer Fault Alert - {transformer_id}"
    
    body = f"""Transformer Fault Detected

Transformer ID: {transformer_id}
City: {city}
Service Station: {service_station}
Health Score: {health_score}%
Predicted Health: {predicted_health}
Fault Type: {fault_type}
Fault Severity: {fault_severity}
Fault Priority: {fault_priority}
Maintenance Status: {maintenance_status}
Detection Time: {device_timestamp}
Google Maps Link: {maps_link}
Nearest Service Station: {nearest_service_station or service_station}
Distance From Fault Location: {f'{distance_km} km' if distance_km is not None else 'N/A'}

Immediate inspection required.
"""

    # ── Dev Fallback Check ────────────────────────────────────────────────────
    # If SMTP settings are not provided, log alert and return True (simulated success)
    if not SMTP_USER or not SMTP_PASSWORD or not ALERT_RECIPIENT_EMAIL:
        logger.warning("SMTP credentials not fully configured. Simulating critical fault email alert:")
        logger.warning(f"\n{'='*70}\n[ALERT SIMULATION] CRITICAL FAULT EMAIL ALERT TRIGGERED\n{'='*70}\nSubject: {subject}\nTo     : {ALERT_RECIPIENT_EMAIL or '[NOT CONFIGURED]'}\n{'-'*70}\n{body}{'='*70}\n")
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
        
        logger.info(f"Alert email dispatched successfully for {transformer_id} to {ALERT_RECIPIENT_EMAIL}.")
        return True
    except Exception as e:
        logger.error(f"Failed to send email alert for {transformer_id}: {e}")
        # Return False to indicate failure
        return False

def send_engineer_assignment_email(transformer_id, fault_type, fault_priority, 
                                   assigned_engineer, engineer_email, 
                                   engineer_phone, assignment_timestamp):
    """
    Sends an SMTP email notification to the assigned engineer when a ticket is assigned.
    """
    subject = f"🛠 Transformer Maintenance Assignment - {transformer_id}"
    
    body = f"""Transformer Maintenance Work Assignment

Transformer ID: {transformer_id}
Fault Type: {fault_type or 'General Degradation'}
Priority: {fault_priority}
Assigned Engineer Name: {assigned_engineer}
Engineer Contact Details: {engineer_phone}
Assignment Timestamp: {assignment_timestamp}

Please proceed to inspect the transformer and resolve the fault.
"""

    # ── Dev Fallback Check ────────────────────────────────────────────────────
    if not SMTP_USER or not SMTP_PASSWORD or not engineer_email:
        logger.warning("SMTP credentials not fully configured. Simulating engineer assignment email notification:")
        logger.warning(f"\n{'='*70}\n[ASSIGNMENT SIMULATION] ENGINEER EMAIL NOTIFICATION TRIGGERED\n{'='*70}\nSubject: {subject}\nTo     : {engineer_email or '[NOT CONFIGURED]'}\n{'-'*70}\n{body}{'='*70}\n")
        return True

    # ── Send Real Email ──────────────────────────────────────────────────────
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_DEFAULT_SENDER
        msg['To'] = engineer_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_DEFAULT_SENDER, [engineer_email], msg.as_string())
        server.quit()
        
        logger.info(f"Assignment email dispatched successfully for {transformer_id} to engineer {engineer_email}.")
        return True
    except Exception as e:
        logger.error(f"Failed to send assignment email alert for {transformer_id}: {e}")
        return False
