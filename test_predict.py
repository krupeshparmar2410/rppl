import pandas as pd
import joblib
import numpy as np
from collections import Counter

model = joblib.load('transformer_health_model.pkl')
feature_list = joblib.load('feature_names.pkl')

df = pd.DataFrame([np.zeros(len(feature_list)), np.ones(len(feature_list))], columns=feature_list)
preds = model.predict(df)
probas = model.predict_proba(df)

if len(preds) > 1:
    pred_code = Counter(preds).most_common(1)[0][0]
    avg_proba = probas.mean(axis=0)
else:
    pred_code = int(preds[0])
    avg_proba = probas[0]

print("pred_code:", pred_code)
print("avg_proba:", avg_proba)
