import pandas as pd
import joblib
import os
from feature_engineering import generate_features

def review_stock_performance(code, universal_model):
    print(f"\n{'='*20} [{code}] 종목 복기 시작 {'='*20}")

    try:
        hist_path = f"C:/program trading system/data_3min/{code}_3min_data.csv"
        live_path = f"C:/program trading system/data/live_data_3min/live_{code}.csv"

        hist_df = pd.read_csv(hist_path, dtype={'date': str})
        live_df = pd.read_csv(live_path, dtype={'date': str})

        combined_df = pd.concat([hist_df, live_df]).drop_duplicates(subset=['date'], keep='last').reset_index(drop=True)
    except FileNotFoundError as e:
        print(f"오류: 데이터 파일을 찾을 수 없습니다. ({e.filename})")
        return

    try:
        model_path = f"C:/program trading system/models/custom_strategists/strategist_{code}.joblib"
        model = joblib.load(model_path)
        print(f"-> 맞춤형 AI 모델 '{os.path.basename(model_path)}' 로드 성공.")
    except FileNotFoundError:
        return
    
    if model is None:
        print(f"-> 분석할 AI 모델이 없어 건너뜁니다.")
        return
    
    print("-> 힌트 및 AI 판단 확률을 계산합니다...")
    features_df = generate_features(combined_df.copy())
    features = [
    'volatility_1h', 'momentum_2h',
    'volatility_ratio', 'volume_weighted_momentum'
    ]

    result_df = features_df.copy()

    if model:
        result_df['custom_proba'] = model.predict_proba(features_df[features])[:, 1]
    else:
        result_df['custom_proba'] = 0.0

    if universal_model:
        result_df['universal_proba'] = universal_model.predict_proba(features_df[features])[:, 1]
    else:
        result_df['universal_proba'] = 0.0

    today_str = pd.to_datetime(live_df['date'].iloc[0], format='%Y%m%d%H%M%S').strftime('%Y-%m-%d')
    result_df['date'] = pd.to_datetime(result_df['date'].astype(str))
    today_trades = result_df[result_df['date'].dt.strftime('%Y-%m-%d') == today_str]

    print("\n--- 오늘 AI의 시간대별 판단 과정 ---")
    print(today_trades[['date', 'close', 'custom_proba', 'universal_proba']].to_string())

if __name__ == "__main__":
    try:
        universal_model_path = "C:/program trading system/models/universal_strategist_optimized.joblib"
        universal_model = joblib.load(universal_model_path)
        print("범용 AI 전략가 모델 로드 성공.")
    except FileNotFoundError:
        print(f"경고: 범용 AI 모델({universal_model_path})을 찾을 수 없습니다.")
        universal_model = None
    try:
        with open("C:/program trading system/watchlist.txt", "r") as f:
            codes_to_review = [line.strip() for line in f if line.strip()]
        if not codes_to_review:
            print("복기할 종목이 watchlist.txt에 없습니다.")
        else:
            for code in codes_to_review:
                code = 234100
                review_stock_performance(code, universal_model)
    except FileNotFoundError:
        print("오류: watchlist.txt 파일을 찾을 수 없습니다.")
    