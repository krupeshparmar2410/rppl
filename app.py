"""
=============================================================================
  AI TRANSFORMER HEALTH MONITORING SYSTEM — Flask Backend
  RPPL Transformers · ML Pipeline Integration
=============================================================================
"""

import os
import io
import json
import math
import time
import random
import datetime
from collections import Counter

import numpy as np
import pandas as pd
import joblib
from flask import Flask, render_template, request, jsonify

# ── App Configuration ─────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'transformer-ai-secret-2024')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024   # 50 MB max upload
ALLOWED_EXTENSIONS = {'csv'}

os.makedirs('uploads', exist_ok=True)

# ── Load ML Model ─────────────────────────────────────────────────────────
model        = None
feature_list = None

def load_model():
    global model, feature_list
    try:
        model        = joblib.load('transformer_health_model.pkl')
        feature_list = joblib.load('feature_names.pkl')
        print(f"[+] Model loaded  : {type(model).__name__}")
        print(f"[+] Features      : {len(feature_list)}")
    except FileNotFoundError as e:
        print(f"[!] Model missing : {e}  — run the notebook first.")

load_model()

# ── Status Mapping ────────────────────────────────────────────────────────
STATUS_MAP = {
    0: {'label':'Normal',   'class':'normal',   'icon':'✅', 'color':'#10B981',
        'action':'No action needed. Continue monitoring.'},
    1: {'label':'Warning',  'class':'warning',  'icon':'⚠️', 'color':'#F59E0B',
        'action':'Monitor closely — plan maintenance soon.'},
    2: {'label':'Critical', 'class':'critical', 'icon':'🔴', 'color':'#EF4444',
        'action':'Schedule IMMEDIATE inspection!'},
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ═════════════════════════════ ROUTES ════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')

# ── Prediction Endpoint ───────────────────────────────────────────────────
@app.route('/predict', methods=['POST'])
def predict():
    if model is None or feature_list is None:
        return jsonify({'success': False,
                        'error': 'ML model not loaded. Run the notebook first.'}), 503

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file in request.'}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Please upload a valid .csv file.'}), 400

    try:
        df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
    except Exception as e:
        return jsonify({'success': False, 'error': f'CSV parse error: {e}'}), 400

    if df.empty:
        return jsonify({'success': False, 'error': 'Uploaded CSV is empty.'}), 400

    # Align columns
    available = [f for f in feature_list if f in df.columns]
    missing   = [f for f in feature_list if f not in df.columns]
    if not available:
        return jsonify({'success': False,
                        'error': f'No matching features. Need: {feature_list[:5]}...'}), 400

    df_model = df[available].copy()
    for col in missing:
        df_model[col] = 0.0
    df_model = df_model[feature_list].fillna(0)

    try:
        preds  = model.predict(df_model)
        probas = model.predict_proba(df_model)
        if len(preds) > 1:
            pred_code = Counter(preds).most_common(1)[0][0]
            avg_proba = probas.mean(axis=0)
        else:
            pred_code = int(preds[0])
            avg_proba = probas[0]
    except Exception as e:
        return jsonify({'success': False, 'error': f'Prediction error: {e}'}), 500

    info = STATUS_MAP.get(int(pred_code), STATUS_MAP[0])
    return jsonify({
        'success'         : True,
        'status'          : info['label'],
        'status_code'     : int(pred_code),
        'status_class'    : info['class'],
        'icon'            : info['icon'],
        'action'          : info['action'],
        'color'           : info['color'],
        'proba_normal'    : round(float(avg_proba[0]) * 100, 2),
        'proba_warning'   : round(float(avg_proba[1]) * 100, 2),
        'proba_critical'  : round(float(avg_proba[2]) * 100, 2),
        'rows_processed'  : len(df),
        'features_used'   : len(available),
        'features_missing': len(missing),
    })

# ── Live Sensor Data API ──────────────────────────────────────────────────
@app.route('/api/live-data')
def live_data():
    t = time.time()
    def noisy(base, amp, freq=0.05):
        return round(base + amp * math.sin(t * freq) + random.uniform(-amp*0.3, amp*0.3), 2)

    health = noisy(87.4, 4.0)
    status_code = 0 if health >= 80 else (1 if health >= 60 else 2)

    return jsonify({
        'vl1': noisy(242.0, 3.0),   'vl2': noisy(241.5, 3.0),  'vl3': noisy(243.0, 3.0),
        'il1': noisy(95.0,  5.0),   'il2': noisy(97.0,  5.0),  'il3': noisy(94.0,  5.0),
        'oti': noisy(46.2,  3.0, 0.02),
        'avg_pf': noisy(0.98, 0.02),
        'kw': noisy(55.4, 5.0),     'kva': noisy(57.0, 5.0),   'kvar': noisy(12.0, 2.0),
        'v_imbalance': noisy(0.31, 0.15),
        'i_imbalance': noisy(1.5,  0.4),
        'health_score': health,
        'failure_prob': noisy(8.3, 2.0),
        'frequency': noisy(50.0, 0.1),
        'status': STATUS_MAP[status_code]['label'],
        'status_code': status_code,
        'timestamp': datetime.datetime.now().isoformat(),
    })

# ── Historical Chart Data API ─────────────────────────────────────────────
@app.route('/api/chart-data')
def chart_data():
    now    = datetime.datetime.now()
    labels = [(now - datetime.timedelta(minutes=(30-i)*5)).strftime('%H:%M') for i in range(30)]

    def series(base, amp, freq=0.2):
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

# ── Error Handlers ────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'error': 'File too large. Max 50MB.'}), 413

# ─────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 55)
    print("  [SYSTEM] TRANSFORMER AI — Health Monitoring System")
    print(f"  Model : {'[READY] Ready' if model else '[ERROR] Not found'}")
    print("  URL   : http://localhost:5000")
    print("=" * 55)
    app.run(debug=True, host='0.0.0.0', port=5000)
