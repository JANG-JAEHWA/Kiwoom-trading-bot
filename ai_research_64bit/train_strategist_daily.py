import pandas as pd
import lightgbm as lgb
import joblib
import os
import optuna
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score

optuna.logging.set_verbosity(optuna.logging.WARNING)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "strategy_training_data.parquet")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "universal_strategist_optimized.joblib")

def objective(trial, X_train, y_train, X_val, y_val, scale_pos_weight):
    params = {
        'objective': 'binary', 'metric': 'binary_logloss', 'verbosity': -1,
        'boosting_type': 'gbdt', 'device': 'gpu', 'random_state': 42,
        'scale_pos_weight': scale_pos_weight,
        'n_estimators': trial.suggest_int('n_estimators', 200, 2000, step=100),
        'learning_rate': trial.suggest_float('learning_rate', 1e-3, 0.1, log=True),
        'num_leaves': trial.suggest_int('num_leaves', 20, 300),
        'max_depth': trial.suggest_int('max_depth', 3, 12),
        'min_child_samples': trial.suggest_int('min_child_samples', 20, 100)
    }
    try:
        model = lgb.LGBMClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[lgb.early_stopping(50, verbose=False)])
        preds = model.predict(X_val)
        if preds.sum() < 20: raise optuna.exceptions.TrialPruned()
        return f1_score(y_val, preds)
    except Exception:
        raise optuna.exceptions.TrialPruned()
    
def main():
    print("--- 범용 AI 전략가 최적화 및 훈련 시작 ---")

    try: df = pd.read_parquet(DATA_PATH)
    except FileNotFoundError: print(f"오류: '{DATA_PATH}' 파일을 찾을 수 없습니다."); return
    
    features = ['volatility_1h', 'momentum_2h', 'volume_ratio', 'atr', 'roc',
                'volatility_of_volatility', 'momentum_acceleration', 'vp_corr_1h']
    X, y = df[features], df['target']

    train_val_size = int(len(X) * 0.8)
    X_train_val, X_test = X[:train_val_size], X[train_val_size:]
    y_train_val, y_test = y[:train_val_size], y[train_val_size:]

    X_train, X_val, y_train, y_val = train_test_split(X_train_val, y_train_val, train_size=0.2, random_state=42)

    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum() if (y_train == 1).sum() > 0 else 1

    print(f"훈련 데이터: {len(X_train)}개, 검증 데이터: {len(X_val)}개, 테스트 데이터: {len(X_test)}개")
    print(f"'BUY' 신호 가중치: {scale_pos_weight:.2f}")

    storage_name = "sqlite:///universal_strategist_study.db"
    study = optuna.create_study(storage=storage_name, study_name="universal_v1", direction='maximize', load_if_exists=True)
    study.optimize(lambda trial: objective(trial, X_train, y_train, X_val, y_val, scale_pos_weight), n_trials=100, show_progress_bar=True)

    print("\n--- 최적화 완료 ---")
    print(f"최고 F1-Score: {study.best_value:.4f}")
    print("최적 하이퍼파라미터:")
    print(study.best_params)

    print("\n최적의 하이퍼파라미터 최종 모델을 훈련합니다...")
    final_params = study.best_params
    final_params['scale_pos_weight'] = scale_pos_weight
    final_model = lgb.LGBMClassifier(**final_params, device='gpu', random_state=42)

    joblib.dump(final_model, MODEL_PATH)
    print(f"\n최적화된 범용 AI 모델을 '{MODEL_PATH}'에 저장했습니다.")

if __name__ == "__main__":
    main()

