import pandas as pd
import numpy as np
from tqdm import tqdm
import pandas_ta as ta
from strategy import ai_strategy
import os

tqdm.pandas()

def run_backtest(df, initial_capital=10000000, atr_multipilier=2.5, fee_tax_rate=0.003):

    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df.dropna(inplace=True)

    cash = initial_capital
    shares = 0
    position_value = 0
    entry_price = 0
    stop_loss_price = 0
    highest_price_since_buy = 0

    trade_count = 0
    win_count = 0

    for i in range(1, len(df)):
        current_price = df['close'].iloc[i]
        current_atr = df['atr'].iloc[i]
        signal = df['target'].iloc[i-1]

        if shares > 0:
            highest_price_since_buy = max(highest_price_since_buy, df['high'].iloc[i])

            trailing_stop_price = highest_price_since_buy - (current_atr * atr_multipilier)
            stop_loss_price = max(stop_loss_price, trailing_stop_price)

            is_time_to_sell = (df.index[i].hour == 15 and df.index[i].minute >= 20)

            if current_price < stop_loss_price or is_time_to_sell:
                sell_value = shares * current_price
                cash += sell_value * (1 - fee_tax_rate)
                
                if current_price > entry_price:
                    win_count += 1
                shares = 0
                position_value = 0
                entry_price = 0
                continue
            
        if shares == 0 and signal == 1:
            shares_to_buy = cash // current_price
            if shares_to_buy > 0:
                buy_value = shares_to_buy * current_price
                cash -= buy_value * (1 + fee_tax_rate)
                shares = shares_to_buy
                position_value = buy_value
                entry_price = current_price
                highest_price_since_buy = current_price

                stop_loss_price = current_price - (current_atr * atr_multipilier)
                trade_count += 1
    final_capital = cash + (shares * df['close'].iloc[-1])
    return final_capital, trade_count, win_count
         
           

def find_optimal_atr_multiplier():
    input_path = "C:/program trading system/data/strategy_training_data.parquet"
    print(f"{input_path} 파일에서 학습 데이터를 불러옵니다...")
    df = pd.read_parquet(input_path)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    atr_multipliers = np.arange(1.5, 4.1, 0.5)

    results = []

    all_codes = df['code'].unique()

    for multiplier in atr_multipliers:
        print(f"\n===== ATR Multiplier = {multiplier} 테스트 시작 =====")

        total_final_capital = 0
        total_trades = 0
        total_wins = 0

        for code in tqdm(all_codes, desc=f"Multiplier {multiplier}"):
            stock_df = df[df['code'] == code].copy()
            if len(stock_df) > 14:
                final_capital, trades, wins = run_backtest(stock_df, atr_multipilier=multiplier)
                total_final_capital += final_capital
                total_trades += trades
                total_wins += wins
        initial_capital_per_stock = 10000000
        total_initial_capital = initial_capital_per_stock * len(all_codes)

        if total_initial_capital > 0:
            avg_return = ((total_final_capital - total_initial_capital) / total_initial_capital) * 100
            win_rate = (total_wins / total_trades) * 100 if total_trades > 0 else 0

            results.append({
                'ATR Multiplier': multiplier,
                'Final Capital': total_final_capital,
                'Average Return (%)': avg_return,
                'Total Trades': total_trades,
                'Win Rate (%)': win_rate
            })
    print("\n===== 최종 최적화 결과 =====")
    result_df = pd.DataFrame(results)
    print(result_df.to_string())
   
if __name__ == "__main__":
    find_optimal_atr_multiplier()
                
                
