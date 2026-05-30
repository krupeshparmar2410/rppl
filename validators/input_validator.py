import pandas as pd

def validate_sensor_data(df, feature_list):
    """
    Validates the uploaded CSV data and generates a Data Quality Report.
    Returns: (is_valid, clean_df, quality_report, error_message)
    """
    # 1. Missing Columns Check
    missing_cols = [f for f in feature_list if f not in df.columns]
    if missing_cols:
        return False, None, None, f"Missing required columns: {missing_cols[:5]}..."
        
    quality_report = {
        'total_rows': len(df),
        'missing_values_count': 0,
        'duplicate_rows': 0,
        'invalid_values': 0,
        'outliers': 0,
        'quality_score': 100
    }
    
    # Check duplicates
    duplicates = df.duplicated().sum()
    quality_report['duplicate_rows'] = int(duplicates)
    
    df_clean = df.drop_duplicates().copy()
    
    # Check missing values
    missing_vals = df_clean[feature_list].isnull().sum().sum()
    quality_report['missing_values_count'] = int(missing_vals)
    df_clean = df_clean.dropna(subset=feature_list)
    
    # Check for invalid values based on physical limits
    invalid_mask = pd.Series(False, index=df_clean.index)
    
    if 'FRQ' in df_clean.columns:
        invalid_mask |= (df_clean['FRQ'] < 45) | (df_clean['FRQ'] > 55)
    if 'VL1' in df_clean.columns:
        invalid_mask |= (df_clean['VL1'] <= 0)
    if 'IL1' in df_clean.columns:
        invalid_mask |= (df_clean['IL1'] <= 0)
    if 'KW' in df_clean.columns:
        invalid_mask |= (df_clean['KW'] < 0)
    if 'OTI' in df_clean.columns:
        invalid_mask |= (df_clean['OTI'] < 0) | (df_clean['OTI'] > 200)
    if 'Load_level' in df_clean.columns:
        invalid_mask |= (df_clean['Load_level'] < 0) | (df_clean['Load_level'] > 150)
        
    invalid_count = invalid_mask.sum()
    quality_report['invalid_values'] = int(invalid_count)
    
    # Filter out strictly invalid rows (outliers can just be flagged)
    df_clean = df_clean[~invalid_mask]
    
    # Calculate Quality Score
    total_issues = duplicates + missing_vals + invalid_count
    score = max(0, 100 - (total_issues / max(1, len(df)) * 100))
    quality_report['quality_score'] = round(score, 1)
    
    if df_clean.empty:
        return False, None, quality_report, "All rows in the uploaded file were invalid or empty."
        
    return True, df_clean, quality_report, None
