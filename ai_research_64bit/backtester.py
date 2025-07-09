import pandas as pd
from tqdm import tqdm
from strategy import ai_strategy
import os

def run_backtest(df, initial_capital=10000000):
    capital = initial_capital
    fee_rate = 0.003
    profit_target = 0.03
    stop_loss_target = -0.015

    position = 0
    buy_price = 0
    trades = []

    for i in tqdm(range(100, len(df)), desc="백테스팅 진행 중"):
        current_price = df.iloc[i]['close']
        current_date = df.iloc[i]['date']

        if position > 0:
            if current_price >= buy_price * (1 + profit_target):
                sell_value = position * current_price
                capital += sell_value * (1 - fee_rate)
                trades.append({'date': current_date, 'type': 'TAKE_PROFIT', 'price': current_price, 'qty': position})
                position = 0
                buy_price = 0
                continue
            elif current_price <= buy_price * (1 + stop_loss_target):
                sell_value = position * current_price
                capital += sell_value * (1 - fee_rate)
                trades.append({'date': current_date, 'type': 'STOP_LOSS', 'price': current_price, 'qty': position})
                position = 0
                buy_price = 0
                continue
        else:
            daily_data = df.iloc[:i+1]
            signal = ai_strategy(daily_data)
            
            if signal == "BUY":
                buy_value = capital
                buy_qty = int(buy_value / current_price)

                if buy_qty > 0:
                    cost = buy_qty * current_price
                    capital -= cost * (1 + fee_rate)
                    position = buy_qty
                    buy_price = current_price
                    trades.append({'date': current_date, 'type': 'BUY', 'price': current_price, 'qty': buy_qty})
    if position > 0:
        last_price = df.iloc[-1]['close']
        capital += position * last_price * (1 - fee_rate)
        trades.append({'date': df.iloc[-1]['date'], 'type': 'EXIT', 'price': last_price, 'qty': position})
    final_balance = capital
    profit = final_balance - initial_capital
    profit_rate = (profit / initial_capital) * 100

    return final_balance, profit, profit_rate, pd.DataFrame(trades)

def main():
    try:
        with open("C:/program trading system/watchlist.txt", "r") as f:
            stock_code_list = f.readlines()
            stock_code = stock_code_list[0].strip() # 몇째 줄 읽기
            if not stock_code:
                print("오류: watchlist.txt 파일이 비어있습니다.")
                return
    except FileNotFoundError:
        print("오류: watchlist.txt 파일을 찾을 수 없습니다. 스카우터를 먼저 실행해주세요.")
        return
    data_path = f"C:/program trading system/data_3min/{stock_code}_3min_data.csv"
    try:
        df = pd.read_csv(data_path, dtype={'date': str})
    except FileNotFoundError:
        print(f"오류: {stock_code}의 데이터 파일을 찾을 수 없습니다.")
        return
    print(f"--- [{stock_code}] 종목 AI 전략 백테스팅 시작 ---")
    final_balance, profit, profit_rate, trade_df = run_backtest(df)

    print("\n--- 백테스팅 결과 ---")
    print(f"최종 자산: {final_balance:,.0f}원")
    print(f"총 손익: {profit:,.0f}원")
    print(f"수익률: {profit_rate:.2f}%")
    print(f"총 거래 횟수: {len(trade_df)}")
    print("\n--- 거래 내역 ---")
    print(trade_df.to_string())

if __name__ == "__main__":
    main()
                
                
