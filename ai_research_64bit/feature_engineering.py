import pandas as pd
import numpy as np

def generate_features(df):
    df_new = df.copy()
    
    df_new['price_change'] = df_new['close'].pct_change()


    df_new['volatility_1h'] = df_new['close'].pct_change().rolling(window=20).std()
    df_new['momentum_2h'] = df_new['close'].pct_change(periods=40)
    df_new['volume_ratio'] = df_new['volume'].rolling(window=20).mean() / (df_new['volume'].rolling(window=100).mean() + 1e-6)

    df_new['volatility_of_volatility'] = df_new['volatility_1h'].rolling(window=20).std()

    df_new['momentum_acceleration'] = df_new['momentum_2h'].pct_change(periods=20)

    df_new['vp_corr_1h'] = df_new['price_change'].rolling(window=20).corr(df_new['volume'])

    high_low = df_new['high'] - df_new['low']
    high_close = np.abs(df_new['high'] - df_new['close'].shift())
    low_close = np.abs(df_new['low'] - df_new['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df_new['atr'] = tr.rolling(window=14).mean()
    df_new['roc'] = df_new['close'].pct_change(periods=20)

    df_new = df_new.drop(columns=['price_change'])
    
    return df_new.dropna()