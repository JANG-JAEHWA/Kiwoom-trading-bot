import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import os

def train_and_evaluate_scout():
    print("--- AI 스카우터 훈련 및 평가 시작---")

    data_path = "C:/program trading system/data/training_data.parquet"
    try:
        df = pd.read_parquet(data_path)
    except FileNotFoundError:
        print(f"오류: 최종 학습 데이터를 찾을 수 없습니다: {data_path}")
        return

    features = ['volatility_1h', 'momentum_2h', 'volume_ratio']
    X = df[features]
    y = df['target']

    train_size = int(len(df) * 0.8)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]
    print(f"훈련 데이터: {len(X_train)}개, 테스터 데이터: {len(X_test)}")

    print("LightGBM 모델 훈련 중...")
    lgb_clf = lgb.LGBMClassifier(
        device= 'gpu',
        n_estimators=1000,         # 더 많은 전문가(트리)에게 물어봅니다.
        learning_rate=0.05,        # 더 꼼꼼하게 학습합니다.
        num_leaves=31,             # 트리의 복잡도
        max_depth=-1,              # 트리의 최대 깊이 (제한 없음)
        random_state=42,
        n_jobs=-1,                 # 사용 가능한 모든 CPU 코어 사용
        colsample_bytree=0.8,      # 훈련 시, 사용할 힌트(Feature)의 비율
        subsample=0.8              # 훈련 시, 사용할 데이터의 비율
    )
    lgb_clf.fit(X_train, y_train,
                eval_set=[(X_test, y_test)],
                eval_metric='logloss',
                callbacks=[lgb.early_stopping(50, verbose=True)])

    predictions = lgb_clf.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(y_test, predictions)
    recall = recall_score(y_test, predictions)

    print("\n--- AI 스카우터 성능 평가 ---")
    print(f"정확도(Accuracy): {accuracy * 100:.2f}%")
    print(f"정밀도(Precision): {precision * 100:.2f}%  (AI가 '상승' 예측한 것 중, 진짜 상승한 비율)")
    print(f"재현율 (Recall): {recall * 100:.2f}%   (실제 상승한 것 중, AI가 '상승' 예측해낸 비율)")

    print("\n--- AI 스카우터의 오늘의 추천 종목 ---")
    latest_data = df.loc[df.groupby('code')['date'].idxmax()]
    latest_x = latest_data[features]

    probabilities = lgb_clf.predict_proba(latest_x)[:, 1]
    latest_data['recommend_proba'] = probabilities

    recommended_stocks = latest_data[latest_data['recommend_proba'] >= 0.5].sort_values(by='recommend_proba', ascending=False)
    
    if recommended_stocks.empty:
        print("오늘은 추천할 만한 종목을 찾지 못했습니다.")
        with open("C:/program trading system/watchlist.txt", "w") as f:
            f.write("")
    else:
        print(recommended_stocks[['code', 'recommend_proba']].head(10))
        recommended_codes = recommended_stocks['code'].tolist()
        with open("C:/program trading system/watchlist.txt", "w") as f:
            for code in recommended_codes:
                f.write(f"{code}\n")
        print("\n'watchlist.txt' 파일에 추천 종목 리스트를 저장했습니다.")

if __name__ == "__main__":
    train_and_evaluate_scout()
