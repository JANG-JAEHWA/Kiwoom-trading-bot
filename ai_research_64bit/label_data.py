import pandas as pd
import numpy as np
from tqdm import tqdm

tqdm.pandas()

def create_labels(df_group):
    """데이터에서 미래의 주가를 보고 정답을 계산하는 함수"""
    PROFIT_TARGET = 0.015
    STOP_LOSS_TARGET = -0.01
    HOLDING_PERIOD = 40

    future_highs = df_group['high'].rolling(window=HOLDING_PERIOD, min_periods=1).max().shift(-HOLDING_PERIOD)
    future_lows = df_group['low'].rolling(window=HOLDING_PERIOD, min_periods=1).max().shift(-HOLDING_PERIOD)
    
    profit_price = df_group['close'] * (1 + PROFIT_TARGET)
    stop_loss_price = df_group['close'] * (1 + STOP_LOSS_TARGET)

    profit_reached = future_highs >= profit_price
    stop_loss_reached = future_lows <= stop_loss_price
 
    df_group['target'] = np.where(profit_reached & ~stop_loss_reached, 1, 0)
    return df_group

def run_labeling():
    parquet_path = "C:/program trading system/data/market_summary.parquet"
    output_path = "C:/program trading system/data/training_data.parquet"

    print(f"'{parquet_path}' 파일을 불러와 라벨링 작업을 시작합니다...")
    df = pd.read_parquet(parquet_path)
    
    print("종목별로 그룹화하여 정답을 계산합니다. (과정이 오래 걸릴 수 있음...)")

    labeled_df = df.groupby('code').progress_apply(create_labels)
    labeled_df = labeled_df.reset_index(drop=True)

    labeled_df.dropna(inplace=True)

    print("\n라벨링 작업 완료. 최종 학습 데이터를 저장합니다...")
    labeled_df.to_parquet(output_path)

    print(f"최종 학습 데이터가 '{output_path}'에 저장되었습니다.")
    print(f"총 {len(labeled_df)}개의 학습 가능한 데이터 포인트가 생성되었습니다.")

if __name__ == "__main__":
    run_labeling()