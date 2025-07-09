import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix
import os
import joblib

def train_and_evaluate_strategist():
    print("--- AI 전략가 훈련 및 평가 시작 ---")

    data_path = "C:/program trading system/data/strategy_training_data.parquet"
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
        random_state=42,
        n_jobs=-1,                 # 사용 가능한 모든 CPU 코어 사용
    )
    lgb_clf.fit(X_train, y_train)

    predictions = lgb_clf.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(y_test, predictions)
    recall = recall_score(y_test, predictions)

    print("\n--- AI 전략가 성능 평가 ---")
    print(f"정확도(Accuracy): {accuracy * 100:.2f}%")
    print(f"정밀도(Precision): {precision * 100:.2f}%  (AI가 '최적 진입점'이라고 예측한 것 중, 진짜였던 비율)")
    print(f"재현율 (Recall): {recall * 100:.2f}%   (실제 '최적 진입점' 중, AI가 찾아낸 비율)")
    print("\n[혼돈 행렬 (confusion Matrix)]")
    print(confusion_matrix(y_test, predictions))

    model_dir = "C:/program trading system/models"
    if not os.path.exists(model_dir): os.makedirs(model_dir)
    model_path = os.path.join(model_dir, 'strategist_model_v1.joblib')
    joblib.dump(lgb_clf, model_path)
    print(f"\n훈련된 AI 전략가 모델을 '{model_path}' 경로에 저장했습니다.")

if __name__ == "__main__":
    train_and_evaluate_strategist()
