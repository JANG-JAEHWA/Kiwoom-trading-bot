import pandas as pd
from strategy import ai_strategy
import os

def run_backtest(data_path, initial_capital=10000000, fee_tax_rate=0.002):
    try:
        df = pd.read_csv(data_path)
        df['date'] = pd.to_datetime(df['date'].astype(str))
        df.set_index('date', inplace=True)
    except FileNotFoundError:
        print(f"데이터 파일을 찾을 수 없습니다: {data_path}")
        return

    cash = initial_capital
    shares = 0
    trade_amount = initial_capital * 0.1
    portfolio_value = initial_capital

    print(f"백테스팅 시작... 초기 자본: {initial_capital:,.0f}원 | 거래 단위: {trade_amount:,.0f}원")

    for i in range(20, len(df)):
        current_data_slice = df.iloc[:i+1]
        current_date = current_data_slice.index[-1]
        current_price = current_data_slice['close'].iloc[-1]

        signal = ai_strategy(current_data_slice)

        if signal == "BUY" and cash > trade_amount:
            if shares == 0:
                buy_qty = trade_amount // (current_price *(1 + fee_tax_rate))
                if buy_qty > 0:
                    cost = buy_qty * current_price
                    cash -= cost * (1 + fee_tax_rate)
                    shares += buy_qty
                    print(f"{current_date} | [매수] {buy_qty}주 @ {current_price:,.0f}원 | 총 현금: {cash:,.0f}원")

        elif signal == "SELL" and shares > 0:
            revenue = shares * current_price
            cash += revenue * (1 - fee_tax_rate)
            print(f"{current_date} | [매도] {shares}주 @ {current_price:,.0f}원 | 총 현금: {cash:,.0f}원")
            shares = 0

    final_portfolio_value = cash + (shares * df['close'].iloc[-1])
    profit = final_portfolio_value - initial_capital
    profit_rate = (profit / initial_capital) * 100

    print("\n--- 백테스팅 결과 ---")
    print(f"최종 자산: {final_portfolio_value:,.0f}원")
    print(f"총 손익: {profit:,.0f}원")
    print(f"수익률: {profit_rate:.2f}%")
    return profit_rate

if __name__ == "__main__":
    csv_path = "data/005930_daily_data.csv"
    run_backtest(csv_path)
                
                
