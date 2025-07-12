import pandas as pd
import numpy as np
from tqdm import tqdm
import pandas_ta as ta
import optuna
import os

tqdm.pandas()

def run_sigle_stock_backtest(df, initial_capital=100000000, atr_multipilier=2.5):

    fee_tax_rate=0.003
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df.dropna(inplace=True)

    cash = initial_capital
    shares = 0
    entry_price = 0
    stop_loss_price = 0
    highest_price_since_buy = 0
    trade_count = 0
    win_count = 0
    trade_amount = initial_capital * 0.1

    for i in range(1, len(df)):
        current_price = df['close'].iloc[i]
        current_atr = df['atr'].iloc[i]
        signal = df['target'].iloc[i-1]

        if shares > 0:
            highest_price_since_buy = max(highest_price_since_buy, df['high'].iloc[i])
            trailing_stop_price = highest_price_since_buy - (current_atr * atr_multipilier)
            stop_loss_price = max(stop_loss_price, trailing_stop_price)

            if current_price < stop_loss_price:
                sell_value = shares * current_price
                cash += sell_value * (1 - fee_tax_rate)
                
                if current_price > entry_price:
                    win_count += 1
                    shares = 0
            
        elif shares == 0 and signal == 1:
            if cash >= trade_amount:
                shares_to_buy = int(trade_amount / current_price)
                if shares_to_buy > 0:
                    buy_value = shares_to_buy * current_price
                    cash -= buy_value * (1 + fee_tax_rate)
                    shares = shares_to_buy
                    entry_price = current_price
                    highest_price_since_buy = current_price
                    stop_loss_price = current_price - (current_atr * atr_multipilier)
                    trade_count += 1
    if shares > 0:
        cash += shares * df['close'].iloc[-1] * (1 - fee_tax_rate)
    return cash, trade_count, win_count
         
def objective(trial, all_stocks_df):
    atr_multiplier = trial.suggest_float('atr_multiplier', 1.0, 5.0)

    total_final_capital = 0
    initial_capital_per_stock = 100000000
    all_codes = all_stocks_df['code'].unique()

    for code in all_codes:
        stock_df = all_stocks_df[all_stocks_df['code'] == code].copy()
        if len(stock_df) > 14:
            final_capital, _, _ = run_sigle_stock_backtest(stock_df, initial_capital_per_stock, atr_multiplier)
            total_final_capital += final_capital
    return total_final_capital

def find_optimal_atr_with_optuna():
    input_path = "C:/program trading system/data/strategy_training_data.parquet"
    print(f"{input_path} 파일에서 학습 데이터를 불러옵니다...")
    df = pd.read_parquet(input_path)
    df['date'] = pd.to_datetime(df['date'].astype(str))
    df = df.set_index('date')
    
    storage_name = "sqlite:///backtest_optimization.db"
    study = optuna.create_study(
        storage=storage_name,
        study_name="atr_stop_optimization.db",
        direction='maximize',
        load_if_exists=True
    )

    study.optimize(lambda trial: objective(trial, df), n_trials=50, show_progress_bar=True)
    print("\n===== 최종 최적화 결과 =====")
    print(f"최고의 성과를 낸 ATR Multiplier: {study.best_params['atr_multiplier']:.4f}")
    print(f"그때의 최종 총 자산: {study.best_value:,.0f} 원")
   
if __name__ == "__main__":
    find_optimal_atr_with_optuna()
                
                
