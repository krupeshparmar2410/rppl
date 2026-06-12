"""
=============================================================================
  AI TRANSFORMER HEALTH MONITORING SYSTEM — Feature Engineering Module
  RPPL Transformers · Feature engineering and data alignment
=============================================================================
"""

import pandas as pd
import numpy as np

# EXPLICIT ASSUMPTION: 
# The active power (KW) is derived from the apparent power (KVA) 
# using an assumed power factor of 0.98, representing a standard 
# efficient power distribution operating condition.
ASSUMED_PF = 0.98

def engineer_transformer_features(df):
    """
    Takes an input DataFrame containing the 11 baseline fields and engineers
    all mathematically derived features. It leaves future IoT fields as NaN
    for database storage.
    """
    df_new = df.copy()

    # 1. Parse Timestamps
    if 'DeviceTimeStamp' in df_new.columns:
        # Convert to datetime series
        dt_series = pd.to_datetime(df_new['DeviceTimeStamp'])
        df_new['Hour'] = dt_series.dt.hour
        df_new['DayOfWeek'] = dt_series.dt.dayofweek
    else:
        df_new['Hour'] = 12
        df_new['DayOfWeek'] = 0

    # 2. Voltage & Current Imbalance
    # V_imbalance = (std(VL1, VL2, VL3) / mean(VL1, VL2, VL3)) * 100
    v_cols = ['VL1', 'VL2', 'VL3']
    if all(c in df_new.columns for c in v_cols):
        v_mean = df_new[v_cols].mean(axis=1)
        v_std = df_new[v_cols].std(axis=1)
        df_new['V_imbalance'] = (v_std / (v_mean + 0.001)) * 100
    else:
        df_new['V_imbalance'] = 0.0

    # I_imbalance = (std(IL1, IL2, IL3) / mean(IL1, IL2, IL3)) * 100
    i_cols = ['IL1', 'IL2', 'IL3']
    if all(c in df_new.columns for c in i_cols):
        i_mean = df_new[i_cols].mean(axis=1)
        i_std = df_new[i_cols].std(axis=1)
        df_new['I_imbalance'] = (i_std / (i_mean + 0.001)) * 100
        df_new['I_total'] = df_new[i_cols].sum(axis=1)
    else:
        df_new['I_imbalance'] = 0.0
        df_new['I_total'] = 0.0

    # 3. Apparent, Active, and Reactive Power Derivation
    # Apparent Power (KVA) = (VL1*IL1 + VL2*IL2 + VL3*IL3) / 1000
    if all(c in df_new.columns for c in ['VL1', 'VL2', 'VL3', 'IL1', 'IL2', 'IL3']):
        df_new['KVA'] = (df_new['VL1'] * df_new['IL1'] + 
                         df_new['VL2'] * df_new['IL2'] + 
                         df_new['VL3'] * df_new['IL3']) / 1000.0
    else:
        df_new['KVA'] = 0.0

    # Active Power (KW) = KVA * assumed_pf
    df_new['KW'] = df_new['KVA'] * ASSUMED_PF

    # Reactive Power (KVAR) = sqrt(KVA^2 - KW^2)
    df_new['KVAR'] = np.sqrt(np.maximum(0.0, df_new['KVA']**2 - df_new['KW']**2))

    # Power Factor Drop (PF_drop) = 1 - assumed_pf = 0.02
    df_new['PF_drop'] = 1 - ASSUMED_PF

    # Load Level = KW / 150.0 (Capacity factor, assumed max transformer capacity 150 kW)
    df_new['Load_level'] = df_new['KW'] / 150.0

    # Power Loss Ratio = KVAR / KVA
    df_new['Power_loss_ratio'] = df_new['KVAR'] / (df_new['KVA'] + 0.001)

    # 4. Set Future IoT-Supported Parameters as NaN (stored as null in MongoDB)
    future_iot_params = [
        'OTI', 'OLI', 'Avg_PF', 'FRQ', 
        'THDVL1', 'THDVL2', 'THDVL3', 
        'THDIL1', 'THDIL2', 'THDIL3', 
        'temperature', 'humidity', 'vibration'
    ]
    for param in future_iot_params:
        if param not in df_new.columns:
            df_new[param] = np.nan

    return df_new

def prepare_for_ml(df, feature_list):
    """
    Fills NaN/null IoT parameters in the DataFrame with standard industrial defaults
    so that the ML model can execute successfully without crashing.
    Returns a DataFrame containing only the 31 columns in feature_list in the correct order.
    """
    df_ml = df.copy()

    # Apply industrial defaults for missing/IoT parameters
    if 'OTI' in df_ml.columns:
        # Check if NaN or OTI exists. If NaN, use default 45.0. If temperature is present, use it.
        if df_ml['OTI'].isnull().all():
            if 'temperature' in df_ml.columns and not df_ml['temperature'].isnull().all():
                df_ml['OTI'] = df_ml['temperature']
            else:
                df_ml['OTI'] = 45.0
        else:
            df_ml['OTI'] = df_ml['OTI'].fillna(45.0)

    if 'OLI' in df_ml.columns:
        df_ml['OLI'] = df_ml['OLI'].fillna(60.0)

    if 'Avg_PF' in df_ml.columns:
        df_ml['Avg_PF'] = df_ml['Avg_PF'].fillna(ASSUMED_PF)

    if 'FRQ' in df_ml.columns:
        df_ml['FRQ'] = df_ml['FRQ'].fillna(50.0)

    # THDs
    thd_v = ['THDVL1', 'THDVL2', 'THDVL3']
    for col in thd_v:
        if col in df_ml.columns:
            df_ml[col] = df_ml[col].fillna(1.2)

    thd_i = ['THDIL1', 'THDIL2', 'THDIL3']
    for col in thd_i:
        if col in df_ml.columns:
            df_ml[col] = df_ml[col].fillna(3.5)

    # OTI-derived features
    if 'Thermal_stress' in df_ml.columns:
        df_ml['Thermal_stress'] = df_ml['OTI'] / 100.0

    if 'OTI_trend' in df_ml.columns:
        # Fill OTI_trend with OTI
        df_ml['OTI_trend'] = df_ml['OTI_trend'].fillna(df_ml['OTI'])

    if 'OTI_change' in df_ml.columns:
        df_ml['OTI_change'] = df_ml['OTI_change'].fillna(0.0)

    if 'KWH' in df_ml.columns:
        df_ml['KWH'] = df_ml['KWH'].fillna(1200.0)

    # Ensure all columns in feature_list exist in df_ml
    for col in feature_list:
        if col not in df_ml.columns:
            df_ml[col] = 0.0

    # Return only the requested features in correct order
    return df_ml[feature_list]

# Document mathematically estimated features for auditability
ESTIMATED_FEATURES = [
    "Hour", "DayOfWeek", "V_imbalance", "I_imbalance", 
    "I_total", "KVA", "KW", "KVAR", "PF_drop", 
    "Load_level", "Power_loss_ratio"
]
