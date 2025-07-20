import pandas as pd
import numpy as np
import lightgbm as lgb
import optuna
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score

optuna.logging.set_verbosity(optuna.logging.WARNING)

DATA_PATH = "C:/program trading system/data/strategy_training_data.parquet"
MODEL_DIR = "C:/program trading system/models/custom_strategists"

try:
    ALL_DATA_DF = pd.read_parquet(DATA_PATH)
except FileNotFoundError:
    print(f"오류: 데이터 파일을 찾을 수 없습니다. - {DATA_PATH}")
    ALL_DATA_DF = None

def find_best_mode_for_stock(stock_df):
    features = ['volatility_1h', 'momentum_2h', 'volume_ratio', 'atr', 'roc',
                'volatility_of_volatility', 'momentum_acceleration', 'vp_corr_1h']
    X, y = stock_df[features], stock_df['target']

    train_size = int(len(X) * 0.7)
    X_train, X_val, y_train, y_val = X[:train_size], X[train_size:], y[:train_size], y[train_size:]

    if (y_train == 1).sum() == 0:
        scale_pos_weight = 1
    else:
        scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    
    scale_pos_weight = min(scale_pos_weight, 100) # 가중치 상한선 설정
    print(f"-> 데이터 불균형 비율 감지. 'BUY' 신호에 {scale_pos_weight:.2f}배의 가중치를 부여합니다.")

    def objective(trial):
        params = {
            'objective': 'binary', 'metric': 'binary_logloss', 'verbosity': -1,
            'boosting_type': 'gbdt', 'device': 'gpu', 'random_state': 42,
            'scale_pos_weight': scale_pos_weight,
            'n_estimators': trial.suggest_int('n_estimators', 200, 1000),
            'learning_rate': trial.suggest_float('learning_rate', 1e-3, 0.1, log=True)
        }
        try:
            model = lgb.LGBMClassifier(**params)
            model.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[lgb.early_stopping(30, verbose=False)])
            preds = model.predict(X_val)
            if preds.sum() < 5:
                raise optuna.exceptions.TrialPruned()
            return f1_score(y_val, preds)
        except Exception:
            raise optuna.exceptions.TrialPruned()

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=50, show_progress_bar=True)
    try:
        best_params = study.best_params
        best_params['scale_pos_weight'] = scale_pos_weight    
        final_model = lgb.LGBMClassifier(**best_params, device='gpu', random_state=42).fit(X, y)
        return final_model, study.best_value
    except ValueError:
        print("-> 모든 시도가 실패하여, 이 종목에 대한 최적 모델을 찾지 못했습니다.")
        return None, 0
def main():
    if ALL_DATA_DF is None: return
    watchlist_path = "C:/program trading system/watchlist.txt"
    try:
        with open(watchlist_path, 'r') as f:
            codes_to_optimize = [line.strip() for line in f if line.strip()]
        if not codes_to_optimize:
            print("최적화할 종목이 watchlist.txt에 없습니다.")
            return
    except FileNotFoundError:
        print(f"{watchlist_path}를 찾을 수 없습니다.")

    print(f"총 {len(codes_to_optimize)}개 종목에 대한 맞춤형 AI 모델 최적화를 시작합니다.")
    os.makedirs(MODEL_DIR, exist_ok=True)

    for code in codes_to_optimize:
        print(f"\n{'='*20} [{code}] 종목 최적화 시작 {'='*20}")
        stock_df = ALL_DATA_DF[ALL_DATA_DF['code'] == code].copy()
        if len(stock_df) < 200:
            print(f"-> 데이터 부족 ({len(stock_df)}개). 건너뜀니다.")
            continue
        best_model, best_f1_score = find_best_mode_for_stock(stock_df)

        if best_model and best_f1_score > 0.1:
            joblib.dump(best_model, os.path.join(MODEL_DIR, f"strategist_{code}.joblib"))
            print(f"-> [{code}] 최적 모델 저장 완료 (F1-Score: {best_f1_score:.4f})")
        else:
            print(f"-> [{code}] 유의미한 모델을 찾지 못해 저장하지 않습니다. (F1-Score: {best_f1_score:.4f})")

if __name__ == "__main__":
    main()