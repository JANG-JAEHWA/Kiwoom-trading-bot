import pandas as pd
import numpy as np
import joblib
import os
from feature_engineering import generate_features
def ai_strategy(daily_data, model_path='C:/program trading system/models/strategist_model_v1.joblib'):
    """
    ai가 판단하여 매수,매도 신호 반환
    """
    try:
        model = joblib.load(model_path)
    except FileNotFoundError:
        print(f"오류: AI 모델 파일이 없음: {model_path}")
        return "HOLD"

    df = pd.DataFrame(daily_data)
    features_df = generate_features(df)
    

    if features_df.empty:
        return "HOLD"

    features = ['volatility_1h', 'momentum_2h', 'volume_ratio']
    latest_features = features_df[features].iloc[[-1]]

    prediction = model.predict(latest_features)

    if prediction[0] == 1:
        return "BUY"
    elif prediction[0] == 2:
        return "SELL"
    else:
        return "HOlD"