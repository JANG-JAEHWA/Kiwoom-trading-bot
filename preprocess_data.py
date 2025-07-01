import pandas as pd
import numpy as np
import os

def create_market_summary():
    print("---시장 요약 데이터 생성 시작---")
    data_dir = "data"
    all_files = [f for f in os.listdir(data_dir) if f.endswith('_daily_data.csv')]

    summary_list = []

    for i, file_name in enumerate(all_files):
        code = file_name.split('-')[0]
        file_path = os.path.join(data_dir, file_name)

        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            print(f"[{i+1}/{len(all_files)}] {code} 파일 읽기 오류: {e}")
            continue
        if len(df) < 30:
            continue
        if 'close' not in df.columns:
            print(f"[{i+1}/{len(all_files)}] {code} 파일에 'close' 칼럼이 없습니다.")
            continue

        df['price_change_ratio'] = df['close'].pct_change()
        latest_return = df['price_change_ratio'].tail(20).mean()

        latest_volatility = df['price_change_ratio'].tail(20).std()

        ma60 = df['close'].rolling(window=60).mean().iloc[-1]
        current_price = df['close'].iloc[-1]
        is_above_ma60 = 1 if current_price > ma60 else 0

        summary =  {
            'code': code,
            'latest_return': latest_return,
            'latest_volatility': latest_volatility,
            'is_above_ma60': is_above_ma60
        }
        summary_list.append(summary)

        if (i+1) % 100 == 0:
            print(f"[{i+1}/{len(all_files)}] {code} 처리 완료...")
    summary_df = pd.DataFrame(summary_list)

    summary_path = os.path.join("data", "market_summary.csv")
    summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')

    print("\n--- 시장 요약 데이터 생성 완료 ---")
    print(f"총 {len(summary_df)}개 종목 분석 완료.")
    print(f"결과가 '{summary_path}'에 저장되었습니다..")
if __name__ == "__main__":
    create_market_summary()
