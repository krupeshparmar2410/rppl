import json
import os
from datetime import datetime

HISTORY_FILE = 'prediction_history.json'

def get_history(limit=5):
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
            return sorted(data, key=lambda x: x['timestamp'], reverse=True)[:limit]
    except:
        return []

def add_history(health_score, status, confidence, total_records):
    record = {
        'timestamp': datetime.now().isoformat(),
        'health_score': round(health_score, 1),
        'status': status,
        'confidence': round(confidence, 1),
        'total_records': total_records
    }
    history = get_history(limit=50)
    history.insert(0, record)
    
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history[:50], f)
    except:
        pass
