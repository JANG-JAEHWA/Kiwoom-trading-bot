import pandas as pd
import numpy as np
import os
from tqdm import tqdm

def create_features(df):
    """3분봉 데이터 프레임에서 변동성, 모멘텀, 거래량 비율을 이용한 미래계산 함수"""
    df['price_change'] = df['close'].pct_change()
    df['volatility_1h'] = df['price_change'].rolling(window=20).std()

    df['momemtum_2h'] = df['close'].pct_change(periods=40)

    df['volume_mean_1h'] = df['volume'].rolling(window=20).mean()
    df['volume_mean_5h'] = df['volume'].rolling(window=100).mean()
    df['volume_ratio'] = df['volume_mean_1h'] / df['volume_mean_5h']

    df = df.drop(columns=['price_change', 'volume_mean_1h', 'volume_mean_5h'])

    return df

def preprocess_all_data():
    data_dir = "C:/program trading system/data_3min"
    all_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]

    all_features_list = []

    for file_name in tqdm(all_files, desc="시장 데이터 요약중"):
        code = file_name.split('_')[0]
        file_path = os.path.join(data_dir, file_name)

        try:
            df = pd.read_csv(file_path, dtype={'date': str})

            if len(df) < 100:
                continue
            
            df_features = create_features(df)

            df_features['code'] = code

            all_features_list.append(df_features)

        except Exception: continue
    
    final_df = pd.concat(all_features_list, ignore_index=True)
    final_df.dropna(inplace=True)

    output_path = "C:/program trading system/data/market_summary_features.csv"
    final_df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"\n\n모든 데이터 처리가 완료되었습니다.")
    print(f"최종 요약 데이터가 '{output_path}'에 저장되었습니다.")
    print(f"총 {len(final_df)}개의 데이터 포인트가 생성되었습니다.")

if __name__ == "__main__":
    preprocess_all_data() 