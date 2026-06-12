"""
=============================================================================
  AI TRANSFORMER HEALTH MONITORING SYSTEM — Flask Backend
  RPPL Transformers · ML Pipeline Integration with MongoDB Atlas
=============================================================================
"""

import os
import io
import time
import datetime
from collections import Counter

import pandas as pd
import numpy as np
import joblib
from flask import Flask, render_template, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename

# Import database, feature engineering, and services modules
from database.mongodb import (
    transformers_col, history_col, insert_prediction, 
    update_alert_sent, update_maintenance_status, get_history, 
    get_dashboard_stats, get_analytics_data, get_transformer_health_timeline
)
from services.feature_engineering import (
    engineer_transformer_features, prepare_for_ml, ASSUMED_PF, ESTIMATED_FEATURES
)
from services.prediction_service import (
    compute_health_score, get_fault_type, get_fault_severity, 
    get_fault_priority, get_maintenance_recommendations, get_reliability
)
from services.email_service import send_fault_alert_email
from utils.logger import get_logger
from utils.error_handlers import register_error_handlers
from validators.input_validator import validate_sensor_data

# ── App Configuration ─────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'transformer-ai-secret-2024')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024   # 50 MB max upload
ALLOWED_EXTENSIONS = {'csv'}

os.makedirs('uploads', exist_ok=True)
logger = get_logger("TransformerApp")

register_error_handlers(app)

# ── Load ML Model ─────────────────────────────────────────────────────────
class ModelManager:
    def __init__(self):
        self.model = None
        self.feature_list = None
        self.version = "1.0.0"
        self.training_date = "2024-05-15"
        
    def load(self):
        try:
            self.model = joblib.load('models/transformer_v1.pkl')
            self.feature_list = joblib.load('models/feature_names.pkl')
            logger.info(f"Model loaded: {type(self.model).__name__}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")

model_manager = ModelManager()
model_manager.load()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ═════════════════════════════ ROUTES ════════════════════════════════════

@app.route('/')
def index():
    # Fetch active list of master transformers for the dropdown
    transformers = list(transformers_col.find({}))
    return render_template('index.html', transformers=transformers)

# ── Health Check Endpoint ─────────────────────────────────────────────────
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

# ── Model Info Endpoint ───────────────────────────────────────────────────
@app.route('/api/model-info')
def model_info():
    return jsonify({
        "model_name": "Transformer Health Monitor",
        "algorithm": type(model_manager.model).__name__ if model_manager.model else "Unknown",
        "version": model_manager.version,
        "features": len(model_manager.feature_list) if model_manager.feature_list else 0,
        "training_date": model_manager.training_date
    })

# ── Prediction Endpoint (CSV upload) ──────────────────────────────────────
@app.route('/predict', methods=['POST'])
def predict():
    start_time = time.time()
    
    if model_manager.model is None or model_manager.feature_list is None:
        return jsonify({'success': False, 'error': 'ML model not loaded.'}), 503

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file in request.'}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Please upload a valid .csv file.'}), 400

    transformer_id = request.form.get('transformer_id', 'TR001')
    
    # Retrieve transformer metadata from master collection
    t_metadata = transformers_col.find_one({"transformer_id": transformer_id})
    if not t_metadata:
        # Default fallback metadata
        t_metadata = {
            "transformer_id": transformer_id,
            "location": "Ahmedabad",
            "service_station": "Ahmedabad Service Center",
            "latitude": 23.0225,
            "longitude": 72.5714
        }

    try:
        df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
    except Exception as e:
        return jsonify({'success': False, 'error': f'CSV parse error: {e}'}), 400

    if df.empty:
        return jsonify({'success': False, 'error': 'Uploaded CSV is empty.'}), 400

    # 1. Feature Engineering (reconstructs 31 features, leaves OTI/OLI/THD as NaN for database)
    try:
        df_engineered = engineer_transformer_features(df)
    except Exception as e:
        logger.error(f"Feature engineering error: {e}")
        return jsonify({'success': False, 'error': f'Feature engineering error: {e}'}), 400

    # 2. Fill standard defaults for ML model compatibility (OTI=45, OLI=60, THD=1.2%)
    try:
        df_ml = prepare_for_ml(df_engineered, model_manager.feature_list)
    except Exception as e:
        logger.error(f"ML preparation error: {e}")
        return jsonify({'success': False, 'error': f'ML preparation error: {e}'}), 400

    # 3. Validation
    is_valid, df_clean, quality_report, err_msg = validate_sensor_data(df_ml, model_manager.feature_list)
    
    if not is_valid:
        return jsonify({
            'success': False, 
            'error': err_msg,
            'quality_report': quality_report
        }), 400

    # 4. Predict on the validated rows
    try:
        # XGBoost or RF predict on feature matrix
        preds = model_manager.model.predict(df_clean)
        probas = model_manager.model.predict_proba(df_clean)
    except Exception as e:
        logger.error(f"Model prediction error: {e}")
        return jsonify({'success': False, 'error': f'Model prediction error: {e}'}), 500

    # Calculate overall summary counts
    total_rows = len(df_clean)
    critical_count = int((preds == 2).sum())
    warning_count = int((preds == 1).sum())
    normal_count = int((preds == 0).sum())
    
    overall_status_code = 2 if (critical_count / total_rows * 100 > 5 or probas[:, 2].max() > 0.95) else (1 if warning_count / total_rows * 100 > 10 else 0)
    overall_status_label = "Critical" if overall_status_code == 2 else ("Warning" if overall_status_code == 1 else "Normal")
    overall_confidence = float(probas.max(axis=1).mean() * 100)
    
    # 5. Insert rows into MongoDB & Trigger Alerts
    inserted_ids = []
    alert_triggered = False
    
    for idx in range(total_rows):
        pred_code = int(preds[idx])
        row_proba = probas[idx]
        
        # Calculate health score for this specific row
        row_ml_risk = float(row_proba[1] + row_proba[2]) # Warning + Critical probability
        row_data = df_clean.iloc[idx].to_dict()
        
        # Pull original engineered features (containing NaNs for future IoT)
        orig_row = df_engineered.iloc[idx].to_dict() if idx < len(df_engineered) else row_data
        
        # Compute degradation metrics
        thermal_stress = float(row_data.get('Thermal_stress', 0.45))
        load_level = float(row_data.get('Load_level', 0.3))
        oti = float(row_data.get('OTI', 45.0))
        pf_drop = float(row_data.get('PF_drop', 0.02))
        power_loss = float(row_data.get('Power_loss_ratio', 0.2))
        
        row_health_score = compute_health_score(row_ml_risk, thermal_stress, load_level, oti, pf_drop, power_loss)
        
        # Determine labels, severity, and priority
        health_label = "Healthy" if pred_code == 0 else ("Warning" if pred_code == 1 else "Critical")
        severity = get_fault_severity(pred_code, row_health_score)
        priority = get_fault_priority(pred_code, row_health_score)
        fault_type = get_fault_type(pred_code, orig_row)
        
        # Construct MongoDB document schema
        db_doc = {
            "transformer_id": transformer_id,
            "DeviceTimeStamp": orig_row.get("DeviceTimeStamp") or datetime.datetime.now().isoformat(),
            "VL1": float(orig_row.get("VL1", 230.0)),
            "VL2": float(orig_row.get("VL2", 230.0)),
            "VL3": float(orig_row.get("VL3", 230.0)),
            "IL1": float(orig_row.get("IL1", 0.0)),
            "IL2": float(orig_row.get("IL2", 0.0)),
            "IL3": float(orig_row.get("IL3", 0.0)),
            "VL12": float(orig_row.get("VL12", float(orig_row.get("VL1", 230.0)) * 1.732)),
            "VL23": float(orig_row.get("VL23", float(orig_row.get("VL2", 230.0)) * 1.732)),
            "VL31": float(orig_row.get("VL31", float(orig_row.get("VL3", 230.0)) * 1.732)),
            "INUT": float(orig_row.get("INUT", 0.0)),
            
            # Future IoT Parameters - stored as null in DB
            "OTI": None,
            "OLI": None,
            "THDVL1": None,
            "THDVL2": None,
            "THDVL3": None,
            "THDIL1": None,
            "THDIL2": None,
            "THDIL3": None,
            "temperature": None, # Stored as null to indicate future IoT sensor parameters
            "humidity": None,
            "vibration": None,
            
            # Calculated ML Outputs & Metadata
            "predicted_health": health_label,
            "fault_type": fault_type,
            "confidence_score": round(float(row_proba[pred_code] * 100), 1),
            "alert_sent": False,
            "maintenance_status": "Pending",
            "fault_severity": severity,
            "fault_priority": priority,
            "assumed_pf": ASSUMED_PF,
            "estimated_features": ESTIMATED_FEATURES
        }
        
        # Save record
        record_id = insert_prediction(db_doc)
        inserted_ids.append(record_id)
        
        # Trigger Email Alert for Critical Fault (P1 or P2)
        if health_label == "Critical" and not alert_triggered:
            # Send alert (email service manages cooldown check)
            alert_sent = send_fault_alert_email(
                transformer_id=transformer_id,
                location=t_metadata.get("location"),
                service_station=t_metadata.get("service_station"),
                latitude=t_metadata.get("latitude"),
                longitude=t_metadata.get("longitude"),
                predicted_health=health_label,
                fault_type=fault_type,
                fault_severity=severity,
                fault_priority=priority,
                health_score=row_health_score,
                maintenance_status="Pending",
                device_timestamp=db_doc["DeviceTimeStamp"]
            )
            if alert_sent:
                update_alert_sent(record_id, True)
                alert_triggered = True

    elapsed_time = time.time() - start_time
    logger.info(f"Processed batch of {total_rows} rows in {elapsed_time:.3f}s. Result: {overall_status_label}")

    status_classes = {0: 'normal', 1: 'warning', 2: 'critical'}
    status_icons = {0: '✅', 1: '⚠️', 2: '🔴'}
    status_colors = {0: '#10B981', 1: '#F59E0B', 2: '#EF4444'}

    # Calculate overall health score for dashboard representation
    # Use average health score of the batch
    overall_health_score = round(float(np.mean([
        compute_health_score(float(probas[i,1] + probas[i,2]),
                             float(df_clean.iloc[i].get('Thermal_stress', 0.45)),
                             float(df_clean.iloc[i].get('Load_level', 0.3)),
                             float(df_clean.iloc[i].get('OTI', 45.0)),
                             float(df_clean.iloc[i].get('PF_drop', 0.02)),
                             float(df_clean.iloc[i].get('Power_loss_ratio', 0.2)))
        for i in range(total_rows)
    ])), 1)

    return jsonify({
        'success'         : True,
        'status'          : overall_status_label,
        'status_code'     : overall_status_code,
        'status_class'    : status_classes[overall_status_code],
        'icon'            : status_icons[overall_status_code],
        'color'           : status_colors[overall_status_code],
        'confidence'      : round(overall_confidence, 1),
        'reliability'     : get_reliability(overall_confidence),
        'health_score'    : overall_health_score,
        'recommendations' : get_maintenance_recommendations(overall_status_code),
        'summary'         : {
            'total_records': total_rows,
            'normal_count': normal_count,
            'warning_count': warning_count,
            'critical_count': critical_count,
            'normal_pct': round(normal_count / total_rows * 100, 1),
            'warning_pct': round(warning_count / total_rows * 100, 1),
            'critical_pct': round(critical_count / total_rows * 100, 1)
        },
        'top_features'    : [],
        'quality_report'  : quality_report,
        'processing_time' : round(elapsed_time, 3)
    })

# ── ESP32 IoT API Integration ─────────────────────────────────────────────
@app.route('/api/sensor-data', methods=['POST'])
def sensor_data():
    """
    API endpoint for real-time ESP32 sensor ingestion.
    Validates, fills missing features, runs inference, saves to MongoDB, 
    manages alert notifications, and returns predictions.
    """
    if model_manager.model is None or model_manager.feature_list is None:
        return jsonify({'success': False, 'error': 'ML model not loaded.'}), 503
        
    data = request.get_json() or {}
    transformer_id = data.get('transformer_id')
    if not transformer_id:
        return jsonify({'success': False, 'error': 'transformer_id is required.'}), 400
        
    # Get master metadata
    t_metadata = transformers_col.find_one({"transformer_id": transformer_id})
    if not t_metadata:
        # Default fallback
        t_metadata = {
            "transformer_id": transformer_id,
            "location": data.get("location", "Gujarat"),
            "service_station": "Gujarat Service Center",
            "latitude": float(data.get("latitude", 22.30)),
            "longitude": float(data.get("longitude", 72.0))
        }

    # Extract readings
    voltage = float(data.get('voltage', 230.0))
    current = float(data.get('current', 0.0))
    temperature = float(data.get('temperature', 45.0))
    
    # Construct Pandas DataFrame for a single row
    row_dict = {
        'DeviceTimeStamp': datetime.datetime.now().isoformat(),
        'VL1': voltage, 'VL2': voltage, 'VL3': voltage,
        'IL1': current, 'IL2': current, 'IL3': current,
        'VL12': voltage * 1.732, 'VL23': voltage * 1.732, 'VL31': voltage * 1.732,
        'INUT': 0.0,
        'temperature': temperature
    }
    
    # Run Feature Engineering
    df_raw = pd.DataFrame([row_dict])
    df_eng = engineer_transformer_features(df_raw)
    
    # Prepare DataFrame for ML model (fill defaults)
    df_ml = prepare_for_ml(df_eng, model_manager.feature_list)
    
    # Run prediction
    try:
        pred_code = int(model_manager.model.predict(df_ml)[0])
        proba = model_manager.model.predict_proba(df_ml)[0]
    except Exception as e:
        return jsonify({'success': False, 'error': f'ML Prediction error: {e}'}), 500

    row_ml_risk = float(proba[1] + proba[2])
    row_health_score = compute_health_score(
        row_ml_risk, 
        temperature / 100.0, 
        (voltage * current * ASSUMED_PF / 1000.0) / 150.0, 
        temperature, 
        1 - ASSUMED_PF, 
        0.2
    )

    health_label = "Healthy" if pred_code == 0 else ("Warning" if pred_code == 1 else "Critical")
    severity = get_fault_severity(pred_code, row_health_score)
    priority = get_fault_priority(pred_code, row_health_score)
    fault_type = get_fault_type(pred_code, row_dict)
    
    # Construct DB record
    db_doc = {
        "transformer_id": transformer_id,
        "DeviceTimeStamp": row_dict["DeviceTimeStamp"],
        "VL1": voltage, "VL2": voltage, "VL3": voltage,
        "IL1": current, "IL2": current, "IL3": current,
        "VL12": voltage * 1.732, "VL23": voltage * 1.732, "VL31": voltage * 1.732,
        "INUT": 0.0,
        "OTI": None, "OLI": None, "THDVL1": None, "THDVL2": None, "THDVL3": None,
        "THDIL1": None, "THDIL2": None, "THDIL3": None,
        "temperature": None, "humidity": None, "vibration": None,
        "predicted_health": health_label,
        "fault_type": fault_type,
        "confidence_score": round(float(proba[pred_code] * 100), 1),
        "alert_sent": False,
        "maintenance_status": "Pending",
        "fault_severity": severity,
        "fault_priority": priority,
        "assumed_pf": ASSUMED_PF,
        "estimated_features": ESTIMATED_FEATURES
    }

    record_id = insert_prediction(db_doc)
    
    # Trigger alert if Critical status (P1/P2)
    alert_sent = False
    if health_label == "Critical":
        alert_sent = send_fault_alert_email(
            transformer_id=transformer_id,
            location=t_metadata.get("location"),
            service_station=t_metadata.get("service_station"),
            latitude=t_metadata.get("latitude"),
            longitude=t_metadata.get("longitude"),
            predicted_health=health_label,
            fault_type=fault_type,
            fault_severity=severity,
            fault_priority=priority,
            health_score=row_health_score,
            maintenance_status="Pending",
            device_timestamp=db_doc["DeviceTimeStamp"]
        )
        if alert_sent:
            update_alert_sent(record_id, True)

    return jsonify({
        "success": True,
        "record_id": record_id,
        "transformer_id": transformer_id,
        "predicted_health": health_label,
        "fault_type": fault_type,
        "fault_severity": severity,
        "fault_priority": priority,
        "health_score": row_health_score,
        "alert_sent": alert_sent
    })

# ── Live Sensor Data API (for front-end dashboard) ────────────────────────
@app.route('/api/live-data')
def live_data():
    from services.simulation_service import generate_live_data
    return jsonify(generate_live_data())

# ── Dashboard Stats API ───────────────────────────────────────────────────
@app.route('/api/dashboard-stats')
def dashboard_stats():
    return jsonify(get_dashboard_stats())

# ── Analytics & Trends API ────────────────────────────────────────────────
@app.route('/api/analytics-data')
def analytics_data():
    return jsonify(get_analytics_data())

# ── Transformer Health Timeline API ────────────────────────────────────────
@app.route('/api/transformer-health-timeline/<transformer_id>')
def transformer_health_timeline(transformer_id):
    return jsonify(get_transformer_health_timeline(transformer_id))

# ── Fault History View Route ──────────────────────────────────────────────
@app.route('/fault-history')
def fault_history():
    search = request.args.get('search')
    sort_by = request.args.get('sort_by', 'timestamp_desc')
    filter_health = request.args.get('filter_health')
    filter_maintenance = request.args.get('filter_maintenance')
    filter_severity = request.args.get('filter_severity')
    filter_priority = request.args.get('filter_priority')
    page = int(request.args.get('page', 1))
    
    records, total = get_history(
        search=search, sort_by=sort_by, filter_health=filter_health,
        filter_maintenance=filter_maintenance, filter_severity=filter_severity,
        filter_priority=filter_priority, page=page, per_page=15
    )
    
    total_pages = max(1, (total + 14) // 15)
    
    # Pass metadata list for filters
    transformers = list(transformers_col.find({}))
    
    return render_template(
        'fault_history.html', 
        records=records, 
        page=page, 
        total_pages=total_pages,
        total_records=total,
        sort_by=sort_by,
        search=search or '',
        filter_health=filter_health or '',
        filter_maintenance=filter_maintenance or '',
        filter_severity=filter_severity or '',
        filter_priority=filter_priority or '',
        transformers=transformers
    )

# ── Update Maintenance Workflow Endpoint ──────────────────────────────────
@app.route('/api/update-maintenance', methods=['POST'])
def update_maintenance():
    data = request.get_json() or {}
    record_id = data.get('record_id')
    status = data.get('status')
    
    if not record_id or not status:
        return jsonify({"success": False, "error": "record_id and status are required."}), 400
        
    allowed_statuses = ["Pending", "Acknowledged", "Assigned", "In Progress", "Resolved"]
    if status not in allowed_statuses:
        return jsonify({"success": False, "error": f"Invalid status. Allowed values: {allowed_statuses}"}), 400
        
    success = update_maintenance_status(record_id, status)
    if success:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Record update failed."}), 500

# ── Reporting Exports (CSV / Excel / PDF) ──────────────────────────────────
@app.route('/fault-history/export/csv')
def export_csv():
    """Exports history to CSV file."""
    records, _ = get_history(page=1, per_page=10000) # Fetch up to 10k records
    if not records:
        return Response("No records available to export.", status=400)
        
    df = pd.DataFrame(records)
    # Filter desired columns for output report
    columns_to_keep = [
        "transformer_id", "location", "service_station", "predicted_health", 
        "fault_severity", "fault_priority", "confidence_score", 
        "maintenance_status", "DeviceTimeStamp"
    ]
    columns_to_keep = [c for c in columns_to_keep if c in df.columns]
    df_out = df[columns_to_keep]
    
    # Rename for professional view
    df_out.columns = [c.replace("_", " ").title() for c in df_out.columns]
    
    csv_buffer = io.StringIO()
    df_out.to_csv(csv_buffer, index=False)
    
    return Response(
        csv_buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=Transformer_Fault_History.csv"}
    )

@app.route('/fault-history/export/excel')
def export_excel():
    """Exports history to Excel (.xlsx) file using openpyxl."""
    records, _ = get_history(page=1, per_page=10000)
    if not records:
        return Response("No records available to export.", status=400)
        
    df = pd.DataFrame(records)
    columns_to_keep = [
        "transformer_id", "location", "service_station", "predicted_health", 
        "fault_severity", "fault_priority", "confidence_score", 
        "maintenance_status", "DeviceTimeStamp"
    ]
    columns_to_keep = [c for c in columns_to_keep if c in df.columns]
    df_out = df[columns_to_keep]
    df_out.columns = [c.replace("_", " ").title() for c in df_out.columns]
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df_out.to_excel(writer, sheet_name="Fault History", index=False)
        
    excel_buffer.seek(0)
    return send_file(
        excel_buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Transformer_Fault_History.xlsx"
    )

@app.route('/fault-history/export/pdf')
def export_pdf():
    """Renders a print-ready HTML page that auto-opens print options (PDF)."""
    # Fetch all records for printing
    records, _ = get_history(page=1, per_page=500)
    return render_template('fault_history_pdf.html', records=records)

# ─────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 55)
    print("  [SYSTEM] TRANSFORMER AI — Health Monitoring System")
    print(f"  Model : {'[READY] Ready' if model_manager.model else '[ERROR] Not found'}")
    print("  URL   : http://localhost:5000")
    print("=" * 55)
    app.run(debug=False, host='0.0.0.0', port=5000)
