import pandas as pd
import joblib
import os

def simple_ma_strategy(daily_data):
    """
    5일 이평선이 20일 이평선을 돌파시 매수 전략
    20일 이평선이 5일 이평선을 돌파시 매도 전략
    """
    if not isinstance(daily_data, pd.DataFrame):
        df = pd.DataFrame(daily_data)
    else:
        df = daily_data.copy()
        
    if len(df) < 20:
        return "HOLD"


    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()

    prev_ma5 = df['MA5'].iloc[-2]
    latest_ma5 = df['MA5'].iloc[-1]
    prev_ma20 = df['MA20'].iloc[-2]
    latest_ma20 = df['MA20'].iloc[-1]

    if prev_ma5 <= prev_ma20 and latest_ma5 > latest_ma20:
        print(">>> 골든크로스 발생! 매수 신호! <<<")
        return "BUY"
    if prev_ma5 >= prev_ma20 and latest_ma5 < latest_ma20:
        print(">>> 데드크로스 발생! 매도 신호! <<<")
        return "SELL"

    return "HOLD"

def ai_strategy(daily_data, model_path='models/ai_model_v1.joblib'):
    """
    ai가 판단하여 매수,매도 신호 반환
    """
    try:
        model = joblib.load(model_path)
    except FileNotFoundError:
        print(f"오류: AI 모델 파일이 없음: {model_path}")
        return "HOLD"

    df = daily_data.copy()
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['price_change_ratio'] = df['close'].pct_change()

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(com=13, min_periods=14).mean()
    avg_loss = loss.ewm(com=13, min_periods=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['bollinger_upper'] = df['MA20'] + (df['close'].rolling(window=20).std() * 2)
    df['bollinger_lower'] = df['MA20'] - (df['close'].rolling(window=20).std() * 2)

    df = df.dropna()

    if df.empty:
        return "HOLD"

    features = ['MA5', 'MA20', 'price_change_ratio', 'volume', 'RSI', 'bollinger_upper', 'bollinger_lower']
    latest_features = df[features].iloc[[-1]]

    prediction = model.predict(latest_features)

    if prediction[0] == 1:
        return "BUY"
    elif prediction[0] == 2:
        return "SELL"
    else:
        return "HOlD"
