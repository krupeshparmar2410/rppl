"""
=============================================================================
  AI TRANSFORMER HEALTH MONITORING SYSTEM — Flask Backend
  RPPL Transformers · ML Pipeline Integration
=============================================================================
"""

import os
import io
import time
import datetime
from collections import Counter

import pandas as pd
import joblib
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# Import our new modules
from utils.logger import get_logger
from utils.error_handlers import register_error_handlers
from validators.input_validator import validate_sensor_data
from services.prediction_service import run_prediction
from services.history_service import add_history
from services.simulation_service import generate_live_data

# ── App Configuration ─────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'transformer-ai-secret-2024')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024   # 50 MB max upload
ALLOWED_EXTENSIONS = {'csv'}

os.makedirs('uploads', exist_ok=True)
logger = get_logger("TransformerApp")

register_error_handlers(app)

# ── Status Mapping ────────────────────────────────────────────────────────
STATUS_MAP = {
    0: {'label':'Normal',   'class':'normal',   'icon':'✅', 'color':'#10B981',
        'action':'No action needed. Continue monitoring.'},
    1: {'label':'Warning',  'class':'warning',  'icon':'⚠️', 'color':'#F59E0B',
        'action':'Monitor closely — plan maintenance soon.'},
    2: {'label':'Critical', 'class':'critical', 'icon':'🔴', 'color':'#EF4444',
        'action':'Schedule IMMEDIATE inspection!'},
}

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
    return render_template('index.html')

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

# ── Prediction Endpoint ───────────────────────────────────────────────────
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

    filename = secure_filename(file.filename)
    
    try:
        # For large files, we could read in chunks, but for now we read all
        # pd.read_csv handles up to 10k rows very quickly
        df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
    except Exception as e:
        return jsonify({'success': False, 'error': f'CSV parse error: {e}'}), 400

    if df.empty:
        return jsonify({'success': False, 'error': 'Uploaded CSV is empty.'}), 400

    # Validation
    is_valid, df_clean, quality_report, err_msg = validate_sensor_data(df, model_manager.feature_list)
    
    if not is_valid:
        return jsonify({
            'success': False, 
            'error': err_msg,
            'quality_report': quality_report
        }), 400

    try:
        # Run advanced prediction logic
        results = run_prediction(model_manager.model, model_manager.feature_list, df_clean)
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({'success': False, 'error': f'Prediction error: {e}'}), 500

    pred_code = results['overall_status_code']
    info = STATUS_MAP.get(pred_code, STATUS_MAP[0])
    
    # Save History
    add_history(
        health_score=results['health_score'],
        status=results['status_label'],
        confidence=results['confidence'],
        total_records=results['summary']['total_records']
    )

    elapsed_time = time.time() - start_time
    logger.info(f"Processed {len(df_clean)} rows in {elapsed_time:.3f}s. Result: {results['status_label']}")

    return jsonify({
        'success'         : True,
        'status'          : results['status_label'],
        'status_code'     : pred_code,
        'status_class'    : info['class'],
        'icon'            : info['icon'],
        'color'           : info['color'],
        'confidence'      : results['confidence'],
        'reliability'     : results['reliability'],
        'health_score'    : results['health_score'],
        'recommendations' : results['recommendations'],
        'summary'         : results['summary'],
        'top_features'    : results['top_features'],
        'quality_report'  : quality_report,
        'processing_time' : round(elapsed_time, 3)
    })

# ── Live Sensor Data API ──────────────────────────────────────────────────
@app.route('/api/live-data')
def live_data():
    return jsonify(generate_live_data())

# ── Historical Chart Data API ─────────────────────────────────────────────
@app.route('/api/chart-data')
def chart_data():
    now = datetime.datetime.now()
    labels = [(now - datetime.timedelta(minutes=(30-i)*5)).strftime('%H:%M') for i in range(30)]

    def series(base, amp, freq=0.2):
        import math, random
        return [round(base + amp*math.sin(i*freq) + random.uniform(-amp*0.3, amp*0.3), 2)
                for i in range(30)]

    return jsonify({
        'labels'      : labels,
        'vl1'         : series(242.0, 4.0),
        'vl2'         : series(241.5, 4.0),
        'vl3'         : series(243.0, 4.0),
        'oti'         : series(46.2,  8.0),
        'v_imbalance' : series(1.2,   1.8),
        'health_score': series(87.4,  10.0),
    })

# ─────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 55)
    print("  [SYSTEM] TRANSFORMER AI — Health Monitoring System")
    print(f"  Model : {'[READY] Ready' if model_manager.model else '[ERROR] Not found'}")
    print("  URL   : http://localhost:5000")
    print("=" * 55)
    # Debug mode is disabled for production readiness
    app.run(debug=False, host='0.0.0.0', port=5000)
