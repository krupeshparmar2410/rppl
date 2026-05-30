import numpy as np
import pandas as pd

def get_maintenance_recommendations(status_code):
    if status_code == 2:
        return [
            "Reduce transformer load immediately.",
            "Inspect cooling system and fans.",
            "Check oil quality and dissolved gases.",
            "Schedule emergency maintenance."
        ]
    elif status_code == 1:
        return [
            "Monitor temperature trends closely.",
            "Review load distribution across phases.",
            "Check cooling efficiency."
        ]
    else:
        return [
            "Continue routine monitoring."
        ]

def get_reliability(confidence):
    if confidence >= 80:
        return "High Reliability"
    elif confidence >= 60:
        return "Medium Reliability"
    else:
        return "Low Reliability"

def compute_health_score(ml_risk_prob, thermal_stress, load_level, oti, pf_drop, power_loss):
    """
    Health Score (0-100)
    100 - (0.4 * ML Risk % + 0.2 * Thermal Stress % + 0.15 * Load Level % + 0.15 * OTI % + 0.05 * PF Drop % + 0.05 * Power Loss %)
    """
    ml_risk_pct = ml_risk_prob * 100
    ts_pct = min(100, max(0, thermal_stress * 50)) 
    load_pct = min(100, max(0, load_level))
    oti_pct = min(100, max(0, (oti - 40) / 80 * 100))
    pf_pct = min(100, max(0, pf_drop * 500))
    pl_pct = min(100, max(0, power_loss * 1000))
    
    penalty = (0.40 * ml_risk_pct + 
               0.20 * ts_pct + 
               0.15 * load_pct + 
               0.15 * oti_pct + 
               0.05 * pf_pct + 
               0.05 * pl_pct)
               
    score = 100 - penalty
    return max(0, min(100, round(score, 1)))

def run_prediction(model, feature_list, df):
    df_model = df[feature_list].copy()
    
    preds = model.predict(df_model)
    probas = model.predict_proba(df_model)
    
    total = len(preds)
    critical_mask = preds == 2
    warning_mask = preds == 1
    normal_mask = preds == 0
    
    critical_count = int(critical_mask.sum())
    warning_count = int(warning_mask.sum())
    normal_count = int(normal_mask.sum())
    
    critical_pct = (critical_count / total) * 100
    warning_pct = (warning_count / total) * 100
    normal_pct = (normal_count / total) * 100
    
    max_critical_prob = probas[:, 2].max() if probas.shape[1] > 2 else 0
    
    # Aggregation Logic
    if critical_pct > 5 or max_critical_prob > 0.95:
        overall_status = 2
    elif warning_pct > 10:
        overall_status = 1
    else:
        overall_status = 0
        
    worst_record_status = int(preds.max())
    highest_risk_idx = int(probas[:, 2].argmax()) if probas.shape[1] > 2 else 0
    
    # Confidence calculation
    confidence = float(probas.max(axis=1).mean() * 100)
    reliability = get_reliability(confidence)
    
    status_label = "Uncertain" if confidence < 60 else ("Critical" if overall_status == 2 else ("Warning" if overall_status == 1 else "Normal"))
    
    # Feature Importance
    try:
        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1]
        top_features = []
        for i in range(min(5, len(indices))):
            top_features.append({
                'feature': feature_list[indices[i]],
                'importance': round(float(importances[indices[i]]), 4)
            })
    except:
        top_features = []
        
    def get_mean(col):
        return float(df[col].mean()) if col in df.columns else 0.0
        
    avg_thermal_stress = get_mean('Thermal_stress')
    avg_load_level = get_mean('Load_level')
    avg_oti = get_mean('OTI')
    avg_pf_drop = get_mean('PF_drop')
    avg_power_loss = get_mean('Power_loss_ratio')
    
    ml_risk = float(probas[:, 1:].sum(axis=1).mean()) if probas.shape[1] > 1 else 0.0
    
    health_score = compute_health_score(
        ml_risk, avg_thermal_stress, avg_load_level, avg_oti, avg_pf_drop, avg_power_loss
    )
    
    summary = {
        'total_records': total,
        'normal_count': normal_count,
        'warning_count': warning_count,
        'critical_count': critical_count,
        'normal_pct': round(normal_pct, 1),
        'warning_pct': round(warning_pct, 1),
        'critical_pct': round(critical_pct, 1),
    }
    
    return {
        'overall_status_code': overall_status,
        'status_label': status_label,
        'worst_record_status': worst_record_status,
        'confidence': round(confidence, 1),
        'reliability': reliability,
        'summary': summary,
        'top_features': top_features,
        'health_score': health_score,
        'recommendations': get_maintenance_recommendations(overall_status)
    }
