import pandas as pd
from strategy import simple_ma_strategy

def run_backtest(data_path, initial_capital=10000000):
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        print(f"데이터 파일을 찾을 수 없습니다: {data_path}")
        return

    cash = initial_capital
    shares = 0
    portfolio_value = initial_capital

    print(f"백테스팅 시작... 초기 자본: {initial_capital:,.0f}원")

    for i in range(20, len(df)):
        current_data_slice = df.iloc[:i+1]

        current_date = current_data_slice['date'].iloc[-1]
        current_price = current_data_slice['close'].iloc[-1]

        signal = simple_ma_strategy(current_data_slice)

        if signal != "HOLD":
            print(f"!!! {current_date} | 특별 신호 발생: {signal} !!!")

        if signal == "BUY" and cash > current_price:
            if shares == 0:
                buy_qty = cash // current_price
                shares += buy_qty
                cash-= buy_qty * current_price
                print(f"{current_date} | [매수] {buy_qty}주 @ {current_price:,.0f}원 | 총 현금: {cash:,.0f}원")

        elif signal == "SELL" and shares > 0:
            cash += shares * current_price
            print(f"{current_date} | [매도] {buy_qty}주 @ {current_price:,.0f}원 | 총 현금: {cash:,.0f}원")

    final_portfolio_value = cash + (shares * df['close'].iloc[-1])
    profit = final_portfolio_value - initial_capital
    profit_rate = (profit / initial_capital) * 100

    print("\n--- 백테스팅 결과 ---")
    print(f"최종 자산: {final_portfolio_value:,.0f}원")
    print(f"총 손익: {profit:,.0f}원")
    print(f"수익률: {profit_rate:.2f}%")

if __name__ == "__main__":
    csv_path = "data/005930_daily_data.csv"
    run_backtest(csv_path)
                
                
