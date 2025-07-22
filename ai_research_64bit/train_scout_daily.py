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
            #'device': 'gpu',
            'random_state': 42
        }
        
def train_and_recommend_daily():
    print("--- AI 스카우터 훈련 및 추천 시작---")

    best_params = get_best_params_from_db()
    #best_params['device'] = 'gpu'
    best_params['random_state'] = 42
    best_params['min_gain_to_split'] = 1e-6
    best_params['min_child_weight'] = 1e-3

    print("\n[적용될 최종 하이퍼파라미터]")
    print(best_params)

    data_path = "C:/program trading system/data/training_data.parquet"
    try:
        df = pd.read_parquet(data_path)
    except FileNotFoundError:
        print(f"오류: 최종 학습 데이터를 찾을 수 없습니다: {data_path}")
        return

    features = [
    'volatility_1h', 'momentum_2h',
    'volatility_ratio', 'volume_weighted_momentum'
    ]
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
        top_candidate = latest_data.sort_values(by='recommend_proba', ascending=False).head(1)
        if not top_candidate.empty:
            print("\n--- 참고: 오늘 가장 확률이 높은 종목 ---")
            print(top_candidate[['code', 'recommend_proba']])
            top_candidate_code = top_candidate['code'].tolist()
            with open(watchlist_path, "w") as f:
                for code in top_candidate_code:
                    f.write(f"{code}\n")
    else:
        top_10_stocks = recommended_stocks.head(10)
        
        print(top_10_stocks[['code', 'recommend_proba']])
        
        recommended_codes = top_10_stocks['code'].tolist()
        with open(watchlist_path, "w") as f:
            for code in recommended_codes:
                f.write(f"{code}\n")
        print(f"\n'{watchlist_path}' 파일에 추천 종목 리스트를 저장했습니다.")

if __name__ == "__main__":
    train_and_recommend_daily()
