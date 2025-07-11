import pandas as pd
import lightgbm as lgb
import joblib
import os
import optuna

def get_best_params_from_db():
    try:
        storage_name = "sqlite:///scout_optimization.db"
        study = optuna.load_study(
            study_name="scout_v1",
            storage=storage_name
        )
        print("Optuna 데이터베이스에서 최적의 하이퍼파라미터를 불러왔습니다.")
        return study.best_params
    except Exception as e:
        print(f"Optuna DB 로딩 실패: {e}")
        print("기본 하이퍼파라미터를 사용합니다.")
        return {
            'device': 'gpu',
            'random_state': 42
        }
        
def train_and_recommend_daily():
    print("--- AI 스카우터 훈련 및 추천 시작---")

    best_params = get_best_params_from_db()
    best_params['device'] = 'gpu'
    best_params['random_state'] = 42

    data_path = "C:/program trading system/data/training_data.parquet"
    try:
        df = pd.read_parquet(data_path)
    except FileNotFoundError:
        print(f"오류: 최종 학습 데이터를 찾을 수 없습니다: {data_path}")
        return

    features = ['volatility_1h', 'momentum_2h', 'volume_ratio', 'atr', 'roc', 'volatility_of_volatility', 'momentum_acceleration', 'vp_corr_1h']
    X = df[features]
    y = df['target']

    print(f"\n총 {len(df)}개의 최신 데이터로 스카우터 모델을 훈련합니다...")
    final_model = lgb.LGBMClassifier(**best_params)
    final_model.fit(X, y)
    print("일일 훈련 완료")

    print("\n--- AI 스카우터의 오늘의 추천 종목 ---")
    latest_data = df.loc[df.groupby('code')['date'].idxmax()]
    latest_X = latest_data[features]

    probabilities = final_model.predict_proba(latest_X)[:, 1]
    latest_data['recommend_proba'] = probabilities

    recommended_stocks = latest_data[latest_data['recommend_proba'] >= 0.5].sort_values(by='recommend_proba', ascending=False)
    
    watchlist_path = "C:/program trading system/watchlist.txt"
    if recommended_stocks.empty:
        print("오늘은 추천할 만한 종목을 찾지 못했습니다.")
        with open(watchlist_path, "w") as f:
            f.write("")
    else:
        print(recommended_stocks[['code', 'recommend_proba']].head(10))
        recommended_codes = recommended_stocks['code'].tolist()
        with open(watchlist_path, "w") as f:
            for code in recommended_codes:
                f.write(f"{code}\n")
        print(f"\n'{watchlist_path}' 파일에 추천 종목 리스트를 저장했습니다.")

if __name__ == "__main__":
    train_and_recommend_daily()
