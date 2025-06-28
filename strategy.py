import pandas as pd

def simple_ma_strategy(daily_data):
    """
    5일 이평선이 20일 이평선을 돌파시 매수 전략
    """
    if not daily_data or len(daily_data) < 20:
        print("[전략 분석 실패] 데이터가 20일치 미만입니다.")
        return "HOLD"

    df = pd.DataFrame(daily_data)
    df = df.iloc[::-1].reset_index(drop=True) #데이터 순서 뒤집음

    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()

    prev_ma5 = df['MA5'].iloc[-2]
    latest_ma5 = df['MA5'].iloc[-1]
    prev_ma20 = df['MA20'].iloc[-2]
    latest_ma20 = df['MA20'].iloc[-1]

    print(f"\n[전략분석] 최신 MA5: {latest_ma5:.0f}, 최신 MA20: {latest_ma20:.0f}")

    if prev_ma5 <= prev_ma20 and latest_ma > latest_ma20:
        print(">>> 골든크로스 발생! 매수 신호! <<<")
        return "BUY"

    print("매수 신호 없음. 관망합니다.")
    return "HOLD"
