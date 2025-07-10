import pandas as pd
import numpy as np

def generate_features(df):
    df_new = df.copy()
    # 변동성
    df_new['volatility_1h'] = df_new['close'].pct_change().rolling(window=20).std()
    # 모멘텀
    df_new['momentum_2h'] = df_new['close'].pct_change(periods=40)
    # 거래량 비율
    df_new['volume_ratio'] = df_new['volume'].rolling(window=20).mean() / (df_new['volume'].rolling(window=100).mean() + 1e-6)
    # ATR, ROC 추가
    high_low = df_new['high'] - df_new['low']
    high_close = np.abs(df_new['high'] - df_new['close'].shift())
    low_close = np.abs(df_new['low'] - df_new['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df_new['atr'] = tr.rolling(window=14).mean()
    df_new['roc'] = df_new['close'].pct_change(periods=20)
    return df_new.dropna()