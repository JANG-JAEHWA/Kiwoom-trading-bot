import pandas as pd
import numpy as np
import pandas_ta as ta
from tqdm import tqdm
import os
import numba

tqdm.pandas()

@numba.jit(nopython=True)
def simulate_trade(close_prices, high_prices, low_prices, atr_values, start_index, atr_multiplier, max_holding_period):
    entry_price = close_prices[start_index]
    entry_atr = atr_values[start_index]

    if np.isnan(entry_atr) or entry_atr == 0:
        return False
    
    stop_loss_price = entry_price - (entry_atr * atr_multiplier)
    highest_price_since_buy = entry_price

    end_index = min(start_index + 1 + max_holding_period, len(close_prices))
    for i in range(start_index + 1, end_index):
        highest_price_since_buy = max(highest_price_since_buy, high_prices[i])
        trailing_stop_price = highest_price_since_buy - (atr_values[i] * atr_multiplier)
        stop_loss_price = max(stop_loss_price, trailing_stop_price)

        if low_prices[i] < stop_loss_price:
            return False
    return True

def label_data_with_atr_stop(group, atr_multiplier, max_holding_period):
    group['atr'] = ta.atr(high=group['high'], low=group['low'], close=group['close'], length=14)
    group.dropna(inplace=True)

    close_prices = group['close'].to_numpy()
    high_prices = group['high'].to_numpy()
    low_prices = group['low'].to_numpy()
    atr_values = group['atr'].to_numpy()

    targets = np.zeros(len(group), dtype=np.int32)

    if len(group) > max_holding_period + 14:
        for i  in range(len(group) - max_holding_period):
            if simulate_trade(close_prices, high_prices, low_prices, atr_values, i, atr_multiplier, max_holding_period):
                targets[i] = 1
    group['target'] = targets
    return group

def main():
    print("--- ATR 트레일링 스톱 기반 전략 데이터 라벨링 사작 ---")

    input_path = "C:/program trading system/data/market_summary.parquet"
    output_path = "C:/program trading system/data/strategy_training_data.parquet"
    ATR_MULTIPLIER = 2.0
    MAX_HOLDING_PERIOD = 40

    try:
        df = pd.read_parquet(input_path)
    except FileNotFoundError:
        print(f"오류: '{input_path}' 파일을 찾을 수 없습니다.")
        return
    
    print(f"총 {df['code'].nunique()}개 종목에 대해 라벨링을 진행합니다...")

    labeled_df = df.groupby('code').progress_apply(lambda x : label_data_with_atr_stop(x, ATR_MULTIPLIER, MAX_HOLDING_PERIOD))

    labeled_df = labeled_df.reset_index(drop=True)
    labeled_df.dropna(inplace=True)
    labeled_df.to_parquet(output_path, index=False)

    print(f"\n라벨링 완료. 결과가 '{output_path}'에 저장되었습니다.")
    print(f"총 데이터 수: {len(labeled_df)}, 'BUY' 라벨 수: {labeled_df['target'].sum()}")

if __name__ == "__main__":
    main()
