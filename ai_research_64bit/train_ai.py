import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from strategy import generate_features
import os
import joblib
import numpy as np

PROJECT_ROOT_PATH = "C:/program trading system"

def train_ai_model(data_path):
    """
    상승/하락 예측 AI모델
    """
    print("\n--- AI 모델 훈련 시작 (v2: 추가 힌트 적용)---")

    try:
        df = pd.read_csv(data_path)
        df = df.sort_values(by='date').reset_index(drop=True)
    except FileNotFoundError:
        print(f"데이터 파일을 찾을 수 없습니다: {data_path}")
        return None, None

    df = generate_features(df)

    price_change = df['close'].shift(-1) / df['close']

    conditions = [
        price_change >= 1.02,
        price_change <= 0.98
    ]
    choices = [1, 2]
    df['target'] = np.select(conditions, choices, default=0)

    df = df.dropna()
    
    features = ['MA5', 'MA20', 'price_change_ratio', 'volume', 'RSI', 'bollinger_upper', 'bollinger_lower']
    x = df[features]
    y = df['target']

    if len(x) == 0:
        print("오류: 훈련할 데이터 없음.")
        return None, None

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, shuffle=False, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(x_train, y_train)

    accuracy = model.score(x_test, y_test)
    print(f"AI 모델 예측 정확도: {accuracy * 100:.2f}%")

    print("--- AI 모델 훈련 완료 ---")
    return model, df

def main():
    print("AI 주가 예측 프로그램을 시작합니다.")

    stock_code = "005930"
    csv_path = os.path.join(PROJECT_ROOT_PATH, "data", f"{stock_code}_daily_data.csv")
    model, full_data = train_ai_model(csv_path)

    if model is None:
        print("모델 훈련 실패 프로그램 종료")
        return
    model_dir = '../models'
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    model_path = os.path.join(model_dir, f'strategist_{stock_code}.joblib')
    joblib.dump(model, model_path)
    print(f"\n훈련된 AI 모델을 '{model_path}' 경로에 저장했습니다.")

    latest_features = full_data[['MA5', 'MA20', 'price_change_ratio', 'volume', 'RSI', 'bollinger_upper', 'bollinger_lower']].iloc[[-1]]

    prediction = model.predict(latest_features)

    print("\n--- AI의 내일 시장 예측 ---")
    if prediction[0] == 1:
        print("결과: 상승 예측, 매수 신호 고려")
    else:
        print("결과: 하락 보합 예측, 보류 매도 고려")

if __name__== "__main__":
    main()
