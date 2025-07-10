import pandas as pd
import numpy as np
import joblib
import os

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

def generate_features(df):
    df_new = df.copy()
    df_new['price_change'] = df_new['close'].pct_change()
    df_new['volatility_1h'] = df_new['price_change'].rolling(window=20).std()

    df_new['momentum_2h'] = df_new['close'].pct_change(periods=40)

    df_new['volume_mean_1h'] = df_new['volume'].rolling(window=20).mean()
    df_new['volume_mean_5h'] = df_new['volume'].rolling(window=100).mean()
    df_new['volume_ratio'] = df_new['volume_mean_1h'] / df_new['volume_mean_5h']

    high_low = df_new['high'] - df_new['low']
    high_close = np.abs(df_new['high'] - df_new['close'].shift())
    low_close = np.abs(df_new['low'] - df_new['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df_new['atr'] = tr.rolling(window=14).mean()

    df_new['roc'] = df_new['close'].pct_change(periods=20)

    df_new = df_new.drop(columns=['price_change', 'volume_mean_1h', 'volume_mean_5h'])

    return df_new.dropna()
    