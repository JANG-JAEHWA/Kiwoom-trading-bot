import pandas as pd
import numpy as np
from tqdm import tqdm
import os

tqdm.pandas()

def create_simple_labels(df_group):
    PROFIT_TARGET = 0.015
    STOP_LOSS_TARGET = -0.01
    HOLDING_PERIOD = 40

    future_highs = df_group['high'].rolling(window=HOLDING_PERIOD, min_periods=1).max().shift(-HOLDING_PERIOD)
    future_lows = df_group['low'].rolling(window=HOLDING_PERIOD, min_periods=1).min().shift(-HOLDING_PERIOD)

    profit_price = df_group['close'] * (1 + PROFIT_TARGET)
    stop_loss_price = df_group['close'] * (1 + STOP_LOSS_TARGET)

    profit_reached = future_highs >= profit_price
    stop_loss_reached = future_lows <= stop_loss_price

    df_group['target'] = np.where(profit_reached & ~stop_loss_reached, 1, 0)

    return df_group

def main():
    print("--- 단순 규칙 기반 전략 데이터 라벨링 사작 ---")

    input_path = "C:/program trading system/data/market_summary.parquet"
    output_path = "C:/program trading system/data/strategy_training_data.parquet"

    try:
        df = pd.read_parquet(input_path)
    except FileNotFoundError:
        print(f"오류: '{input_path}' 파일을 찾을 수 없습니다.")
        return
    
    print(f"총 {df['code'].nunique()}개 종목에 대해 라벨링을 진행합니다...")

    labeled_df = df.groupby('code').progress_apply(create_simple_labels)

    labeled_df = labeled_df.reset_index(drop=True)
    labeled_df.dropna(inplace=True)

    labeled_df.to_parquet(output_path, index=False)

    print(f"\n라벨링 완료. 결과가 '{output_path}'에 저장되었습니다.")
    print(f"총 데이터 수: {len(labeled_df)}, 'BUY' 라벨 수: {labeled_df['target'].sum()}")

if __name__ == "__main__":
    main()
