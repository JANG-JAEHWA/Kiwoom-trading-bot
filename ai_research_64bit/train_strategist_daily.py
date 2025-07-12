import pandas as pd
import lightgbm as lgb
import joblib
import os
import optuna

def get_best_params_from_db():
    try:
        storage_name = "sqlite:///strategist_optimization.db"
        study = optuna.load_study(
            study_name="strategist_v1",
            storage=storage_name
        )
        print("Optuna 데이터베이스에서 최적의 하이퍼파라미터를 성공적으로 불러왔습니다.")
        return study.best_params
    except Exception as e:
        print(f"Optuna DB 로딩 실패: {e}")
        print("기본 하이퍼파라미터를 사용합니다.")
        return {
            'n_estimators': 549,
            'learning_rate': 0.013382611503393602,
            'num_leaves': 72,
            'max_depth': 3,
            'device': 'gpu',
            'random_state': 42
        }

def train_daily_strategist():
    print("--- AI 전략가 일일 훈련 시작 (최적화된 파라미터 사용) ---")

    best_params = get_best_params_from_db()

    best_params['device'] = 'gpu'
    best_params['random_state'] = 42

    print("\n[적용될 하이퍼파라미터]")
    print(best_params)
    
    data_path = "C:/program trading system/data/strategy_training_data.parquet"
    try:
        df = pd.read_parquet(data_path)
    except FileNotFoundError:
        print(f"오류: {data_path} 파일을 찾을 수 없습니다.")
        return
    features = ['volatility_1h', 'momentum_2h', 'volume_ratio', 'atr', 'roc', 'volatility_of_volatility', 'momentum_acceleration', 'vp_corr_1h']
    X, y = df[features], df['target']

    print(f"총 {len(df)}개의 최신 데이터로 모델을 훈련합니다...")
    final_model = lgb.LGBMClassifier(**best_params)
    final_model.fit(X, y)

    model_path = "C:/program trading system/models/strategist_model_daily.joblib"
    joblib.dump(final_model, model_path)
    print(f"\n일일 훈련 완료. 최신 모델을 '{model_path}'에 저장했습니다.")

if __name__ == "__main__":
    train_daily_strategist()