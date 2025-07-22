import pandas as pd
import numpy as np

def generate_features(df):
    df_new = df.copy()
    
    df_new['price_change'] = df_new['close'].pct_change()


    df_new['volatility_1h'] = df_new['close'].pct_change().rolling(window=20).std()
    df_new['momentum_2h'] = df_new['close'].pct_change(periods=40)

    volatility_6h = df_new['price_change'].rolling(window=120).std()
    df_new['volatility_ratio'] = df_new['volatility_1h'] / (volatility_6h + 1e-6)

    df_new['volume_weighted_momentum'] = df_new['momentum_2h'] * df_new['volume']

    df_new = df_new.drop(columns=['price_change'])
    
    return df_new.dropna()