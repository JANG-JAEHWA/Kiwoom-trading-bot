import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import os
import joblib

def train_scout_model():
    print("--- AI 스카우터 훈련 시작---")

    summary_path = os.path.join("data", "market_summary.csv")
    try:
        df = pd.read_csv(summary_path)
    except:
        print("오류 요약 데이터를 찾을 수 없습니다.")
        return
    df['target'] = ((df['latest_return'] > 0.005) & (df['is_above_ma60'] == 1)).astype(int)

    df = df.dropna()

    features = ['latest_return', 'latest_volatility', 'is_above_ma60']
    x = df[features]
    y = df['target']

    if len(x) == 0 or len(y.unique()) < 2:
        print("오류: 훈련할 데이터가 부족하거나, 한 종류의 정답만 존재")
        return

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(x_train, y_train)

    accuracy = model.score(x_test, y_test)
    print(f"AI 스카우터 정확도: {accuracy * 100:.2f}%")

    df['prediction'] = model.predict(x)
    recommended_stocks = df[df['prediction'] == 1]

    print("\n--- AI 스카우터 최종 추천 종목 ---")
    if recommended_stocks.empty:
        print("추천할 만한 종목을 찾지 못했습니다.")
    else:
        print(recommended_stocks[['code', 'latest_return', 'latest_volatility']])

    if not os.path.exists('models'):
        os.makedirs('models')
    model_path = os.path.join('models', 'scout_model_v1.joblib')
    joblib.dump(model, model_path)
    print("훈련된 스카우터 모델을 저장했습니다.")

if __name__ == "__main__":
    train_scout_model()
