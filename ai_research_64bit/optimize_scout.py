import pandas as pd
import lightgbm as lgb
import joblib
import os
import optuna
from sklearn.metrics import precision_score

def objective(trial, X_train, y_train, X_val, y_val):
    params = {
        'objective': 'binary',
        'metric': 'binary_logloss',
        'verbosity': -1,
        'boosting_type': 'gbdt',
        'device': 'gpu',
        'random_state': 42,
        'n_estimators': trial.suggest_int('n_estimators', 100, 2000),
        'learning_rate': trial.suggest_float('learning_rate', 1e-3, 0.1, log=True),
        'num_leaves': trial.suggest_int('num_leaves', 20, 300),
        'max_depth': trial.suggest_int('max_depth', 3, 12),
        'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0)
    }
    try:
        model = lgb.LGBMClassifier(**params)
        model.fit(X_train, y_train,
                eval_set=[(X_val, y_val)],
                eval_metric='logloss',
                callbacks=[lgb.early_stopping(50, verbose=False)])
        preds = model.predict(X_val)
        precision = precision_score(y_val, preds)
        return precision
    except lgb.basic.LightGBMError:
        raise optuna.exceptions.TrialPruned()
    
def train_and_optimize_scout():
    print("--- AI 스카우터 하이퍼파라미터 최적화 시작 ---")

    data_path = "C:/program trading system/data/training_data.parquet"
    try:
        df = pd.read_parquet(data_path)
    except FileNotFoundError:
        print(f"오류: 최종 학습 데이터를 찾을 수 없습니다: {data_path}")
        return
    
    features = ['volatility_1h', 'momentum_2h', 'volume_ratio', 'atr', 'roc', 'volatility_of_volatility', 'momentum_acceleration', 'vp_corr_1h']
    X = df[features]
    y = df['target']

    train_size = int(len(df) * 0.7)
    val_size = int(len(df) * 0.1)
    X_train = X[:train_size]
    y_train = y[:train_size]
    X_val, y_val = X[train_size:train_size+val_size], y[train_size:train_size+val_size]

    print(f"훈련 데이터: {len(X_train)}개, 검증 데이터: {len(X_val)}개, 테스터 데이터: {len(X_test)}")

    storage_name = "sqlite:///scout_optimization.db"
    study = optuna.create_study(
        storage=storage_name,
        study_name="scout_v1",
        direction='maximize',
        load_if_exists=True
    )
    study.optimize(lambda trial: objective(trial, X_train, y_train, X_val, y_val), n_trials=100, show_progress_bar=True)

    print("\n--- 최적화 완료 ---")
    print(f"스카우터 최고 정밀도: {study.best_value:.4f}")
    print("스카우터 최적 하이퍼파라미터:")
    print(study.best_params)

if __name__ == "__main__":
    train_and_optimize_scout()