import time
import math
import random
from datetime import datetime

# Keep some state to calculate trends
history_oti = []
history_load = []
history_ts = []

def get_trend(values):
    if len(values) < 2: return "→"
    recent = values[-1]
    older = values[0]
    if recent > older * 1.05: return "↑"
    if recent < older * 0.95: return "↓"
    return "→"

def generate_live_data():
    global history_oti, history_load, history_ts
    
    t = time.time()
    def sinusoidal(base, amp, freq=0.05):
        return round(base + amp * math.sin(t * freq) + random.uniform(-amp*0.1, amp*0.1), 2)
        
    oti = sinusoidal(46.2, 5.0, 0.01)
    load = sinusoidal(39.2, 10.0, 0.02)
    ts = sinusoidal(0.18, 0.05, 0.01)
    
    history_oti.append(oti)
    history_load.append(load)
    history_ts.append(ts)
    
    if len(history_oti) > 10: history_oti.pop(0)
    if len(history_load) > 10: history_load.pop(0)
    if len(history_ts) > 10: history_ts.pop(0)

    health = sinusoidal(87.4, 4.0, 0.01)
    status_code = 0 if health >= 80 else (1 if health >= 60 else 2)

    return {
        'vl1': sinusoidal(242.0, 2.0),   'vl2': sinusoidal(241.5, 2.0),  'vl3': sinusoidal(243.0, 2.0),
        'il1': sinusoidal(95.0,  3.0),   'il2': sinusoidal(97.0,  3.0),  'il3': sinusoidal(94.0,  3.0),
        'oti': oti,
        'oti_trend': get_trend(history_oti),
        'avg_pf': sinusoidal(0.98, 0.01),
        'kw': sinusoidal(55.4, 2.0),     'kva': sinusoidal(57.0, 2.0),   'kvar': sinusoidal(12.0, 1.0),
        'v_imbalance': sinusoidal(0.31, 0.05),
        'i_imbalance': sinusoidal(1.5,  0.2),
        'health_score': health,
        'failure_prob': sinusoidal(8.3, 1.0),
        'frequency': sinusoidal(50.0, 0.05),
        'status': 'Normal' if status_code == 0 else ('Warning' if status_code == 1 else 'Critical'),
        'status_code': status_code,
        'load_level': load,
        'load_trend': get_trend(history_load),
        'thermal_stress': ts,
        'ts_trend': get_trend(history_ts),
        'timestamp': datetime.now().isoformat(),
    }
