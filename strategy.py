import pandas as pd

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
