import pandas as pd
from strategy import generate_features
import joblib
import os
import time

STOCK_CODE = "005930"
LIVE_DATA_PATH = "../data/live_data.csv"
MODEL_PATH = f"../models/strategist_{STOCK_CODE}.joblib"
SIGNAL_PATH = "../signal.txt"

def load_latest_data():
    try:
        return pd.read_csv(LIVE_DATA_PATH)
    except:
        return None
    
def make_prediction(model, live_data: pd.DataFrame) -> str:
    features_df = generate_features(live_data)

    if  features_df.empty:
        return "HOLD"
    features = ['MA5', 'MA20', 'price_change_ratio', 'volume', 'RSI', 'bollinger_upper', 'bollinger_lower']
    latest_features = features_df[features].iloc[[-1]]

    prediction = model.predict(latest_features)

                        
    if prediction[0] == 1:
        return "BUY"
    elif prediction[0] == 2:
        return "SELL"
    return "HOLD"

def write_signal(signal: str):
    if signal != "HOLD":
        if not os.path.exists(SIGNAL_PATH):
            with open(SIGNAL_PATH, 'w') as f:
                f.write(f"{signal},{STOCK_CODE},1")
            print(f"!!! 주문 신호 생성: {signal} -> '{SIGNAL_PATH}' 파일에 저장")
        else:
            print("이미 처리 대기 중인 신호가 있습니다.")

def run_ai_controller():
    print("--- AI 컨트롤러 시작 ---")

    try:
        model = joblib.load(MODEL_PATH)
        print("AI 전략가 모델을 성공적으로 불러왔습니다.")
    except FileNotFoundError:
        print("AI모델을 찾을 수 없습니다.")
        return
    last_processed_time = None
    while True:
        try:
            if os.path.exists(LIVE_DATA_PATH):
                current_mod_time = os.path.getmtime(LIVE_DATA_PATH)
                if current_mod_time != last_processed_time:
                    last_processed_time = current_mod_time
                    print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')} | 새로운 캔들 데이터 감지. 분석 시작...")

                    live_df = load_latest_data(LIVE_DATA_PATH)
                    if live_df is not None:
                        signal = make_prediction(model, live_df)
                        print(f"AI 판단: {signal}")
                        write_signal(signal)               
            time.sleep(60)
        except KeyboardInterrupt:
            print("\nAI 컨트롤러를 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_ai_controller()
