import pandas as pd
import numpy as np
from feature_engineering import generate_features
import os
from tqdm import tqdm

MIN_AVG_TRADING_VALUE = 1_000_000_000

def preprocess_all_data():
    data_dir = "C:/program trading system/data_3min"
    all_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]

    all_features_list = []

    for file_name in tqdm(all_files, desc="시장 데이터 요약중"):
        code = file_name.split('_')[0]
        file_path = os.path.join(data_dir, file_name)

        try:
            df = pd.read_csv(file_path, dtype={'date': str})

            if len(df) < 101:
                continue
            df['trading_value'] = df['close'] * df['volume']
            df['day'] = df['date'].str[:8]
            avg_trading_value = df.groupby('day')['trading_value'].sum().mean()

            if avg_trading_value < MIN_AVG_TRADING_VALUE:
                continue
            df.drop(columns=['trading_value', 'day'], inplace=True)
            
            df_features = generate_features(df)

            df_features.replace([np.inf, -np.inf], np.nan, inplace=True)
            df_features.dropna(inplace=True)

            df_features['code'] = code
            all_features_list.append(df_features)

        except Exception: continue
    
    final_df = pd.concat(all_features_list, ignore_index=True)

    output_path = "C:/program trading system/data/market_summary.parquet"
    final_df.to_parquet(output_path, index=False)

    print(f"\n\n모든 데이터 처리가 완료되었습니다.")
    print(f"최종 요약 데이터가 '{output_path}'에 저장되었습니다.")
    print(f"총 {len(final_df)}개의 데이터 포인트가 생성되었습니다.")

if __name__ == "__main__":
    preprocess_all_data() 