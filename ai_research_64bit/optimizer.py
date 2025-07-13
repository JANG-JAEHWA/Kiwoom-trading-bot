import pandas as pd
import numpy as np
import pandas_ta as ta
import lightgbm as lgb
import optuna
import joblib
import os
import random
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score

optuna.logging.set_verbosity(optuna.logging.WARNING)

DATA_PATH = "C:/program trading system/data/strategy_training_data.parquet"
MODEL_DIR = "C:/program trading system/models/custum_strategists"
RULES_DIR = "C:/program trading system/rules"

try:
    ALL_DATA_DF = pd.read_parquet(DATA_PATH)
    ALL_DATA_DF['date'] = pd.to_datetime(ALL_DATA_DF['date'].astype(str))
    ALL_DATA_DF = ALL_DATA_DF.set_index('date')
except FileNotFoundError:
    print(f"오류: 데이터 파일을 찾을 수 없습니다. - {DATA_PATH}")
    ALL_DATA_DF = None

def optimize_for_stock(code):
    if ALL_DATA_DF is None: return

    print(f"\n{'='*20} [{code}] 종목 최적화 시작 {'='*20}")

    stock_df = ALL_DATA_DF[ALL_DATA_DF['code'] == code].copy()
    if len(stock_df) < 200:
        print(f"[{code}] 데이터가 너무 적어 최적화를 건너뜁니다. (데이터 수: {len(stock_df)})")
        return
    
    print(f"\n--- 1. [{code}] 진입 전략 (AI 모델) 최적화 중...")
    best_model = find_best_entry_model(stock_df)
    if best_model is None:
        print(f"[{code}] 최적의 진입 모델을 찾지 못했습니다.")
        return
    
    print(f"\n--- 2. [{code}] 청산 전략 (ATR 배수) 최적화 중...")
    best_atr_multiplier = find_best_exit_rule(stock_df, best_model)
    if best_atr_multiplier is None:
        print(f"[{code}] 최적의 청산 규칙을 찾지 못했습니다.")
        return

    save_optimal_results(code, best_model, best_atr_multiplier)
    print(f"\n{'='*20} [{code}] 종목 최적화 완료 {'='*20}")

def find_best_entry_model(stock_df):
    features = ['volatility_1h', 'momentum_2h', 'volume_ratio', 'atr', 'roc', 'volatility_of_volatility', 'momentum_acceleration', 'vp_corr_1h']
    X, y = stock_df[features], stock_df['target']
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    def objective(trial):
        params = {
            'objective': 'binary', 'metric': 'binary_logloss', 'verbosity': -1,
            'boosting_type': 'gbdt', 'device': 'gpu', 'random_state': 42,
            'n_estimators': trial.suggest_int('n_estimators', 200, 1000, step=100),
            'learning_rate': trial.suggest_float('learning_rate', 1e-4, 1e-1, log=True),
            'num_leaves': trial.suggest_int('num_leaves', 20, 300),
            'max_depth': trial.suggest_int('max_depth', 3, 10)
        }
        model = lgb.LGBMClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[lgb.early_stopping(50, verbose=False)])
        preds = model.predict(X_val)
        return precision_score(y_val, preds)

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=50, show_progress_bar=True)

    best_model = lgb.LGBMClassifier(**study.best_params).fit(X, y)
    return best_model

def find_best_exit_rule(stock_df, model):
    def backtest_objective(trial):
        atr_multiplier = trial.suggest_float('atr_multiplier', 1.0, 5.0)

        df = stock_df.copy()
        df['signal'] = model.predict (df[['volatility_1h', 'momentum_2h', 'volume_ratio', 'atr', 'roc', 'volatility_of_volatility', 'momentum_acceleration', 'vp_corr_1h']])

        initial_capital = 10000000
        cash = initial_capital
        shares =  0
        trade_amount = initial_capital * 0.1

        for i in range(1, len(df)):
            current_price = df['close'].iloc[i]
            signal = df['signal'].iloc[i-1]

            if shares > 0:
                if current_price < stop_loss_price:
                    cash += shares * current_price *0.997
                    shares = 0
            elif shares == 0 and signal == 1:
                if cash >= trade_amount:
                    shares_to_buy = int(trade_amount / current_price)
                    if shares_to_buy > 0:
                        cash -= shares_to_buy * current_price * 1.003
                        shares = shares_to_buy
                        stop_loss_price = current_price - (df['atr'].iloc[i] * atr_multiplier)
        if shares > 0:
            cash += shares * df['close'].iloc[-1] * 0.997

        return ((cash - initial_capital) / initial_capital) * 100
    
    study = optuna.create_study(direction='maximize')
    study.optimize(backtest_objective, n_trials=50, show_progress_bar=True)
    return study.best_params['atr_multiplier']

def save_optimal_results(code, model, atr_multiplier):
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, os.path.join(MODEL_DIR, f"strategist_{code}.joblib"))
    print(f"-> 최적 모델 저장 완료: strategist_{code}.joblib")

    os.makedirs(RULES_DIR, exist_ok=True)
    rules_path = os.path.join(RULES_DIR, "optimal_rules.json")

    all_rules = {}
    if os.path.exists(rules_path):
        with open(rules_path, 'r') as f:
            all_rules = json.load(f)

    all_rules[code] = {'atr_multiplier': atr_multiplier}

    with open(rules_path, 'w') as f:
        json.dump(all_rules, f, indent=4)
    print(f"-> 최적 규칙 저장 완료: optimal_rules.json에 [{code}] 정보 업데이트")

if __name__ == "__main__":
    watchlist_path = "C:/program trading system/watchlist.txt"
    try:
        with open(watchlist_path, 'r') as f:
            codes_to_optimize = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"{watchlist_path}를 찾을 수 없습니다.")

    for code in codes_to_optimize:
        optimize_for_stock(code)