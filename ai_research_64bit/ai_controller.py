import pandas as pd
from strategy import generate_features
import joblib
import os
import time

WATCHLIST_PATH = "C:/program trading system/watchlist.txt"
STRATEGIST_MODEL_PATH = f"C:/program trading system/models/strategist_model_v1.joblib"
LIVE_DATA_DIR = "C:/program trading system/data/live_data"
SIGNAL_DIR = "C:/program trading system/signals"

def load_live_data(code):
    path = os.path.join(LIVE_DATA_DIR, f"live_{code}.csv")
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        return None

def laod_historical_data(code):
    path = f"C:/program trading system/data_3min/{code}_3min_data.csv"
    try:
        return pd.read_csv(path, dtype={'date': str})
    except FileExistsError:
        print(f"[{code}] 과거 데이터 파일을 찾을 수 없습니다.")
        return None

def run_ai_controller():
    print("--- AI 컨트롤러 시작 ---")

    try:
        strategist_model = joblib.load(STRATEGIST_MODEL_PATH)
        print("AI 전략가 모델을 성공적으로 불러왔습니다.")
    except FileNotFoundError:
        print(f"AI모델을 찾을 수 없습니다: {STRATEGIST_MODEL_PATH}")
        return
    
    if not os.path.exists(LIVE_DATA_DIR): os.makedirs(LIVE_DATA_DIR)
    if not os.path.exists(SIGNAL_DIR): os.makedirs(SIGNAL_DIR)

    last_mod_times = {}
    while True:
        try:
            with open(WATCHLIST_PATH, 'r') as f:
                watchlist = [line.strip() for line in f.readline()]
            if not watchlist:
                print("관심 종목 없음. 대기 중...", end='\r')
                time.sleep(10)
                continue
            for code in watchlist:
                live_data_path = os.path.join(LIVE_DATA_DIR, f"live_{code}.csv")
                if os.path.exists(live_data_path):
                    current_mod_time = os.path.getatime(live_data_path)

                    if current_mod_time != last_processed_time:
                        last_processed_time = current_mod_time
                        print(f"\n[{code}, {time.strftime('%Y-%m-%d %H:%M:%S')}] | 새로운 캔들 데이터 감지. 분석 시작...")
                        
                        historical_df = laod_historical_data(code)
                        live_df = load_live_data(code)

                        if historical_df is None or live_df is None:
                            continue
                        combined_df = pd.concat([historical_df, live_df]).drop_duplicates(subset=['date'], keep='last')
                        if len(combined_df) > 100:
                            features_df = generate_features(combined_df)
                            features = ['volatility_1h', 'momentum_2h', 'volume_ratio']
                            latest_features = features_df[features].iloc[[-1]]

                            prediction = strategist_model.predict(latest_features)

                            signal = "HOLD"
                            if prediction[0] == 1: signal = "BUY"
                            elif prediction[0] == 2: signal = "SELL"

                            print(f"-> AI 판단: [{code}] {signal}")

                            if signal != "HOLD":
                                signal_path = os.path.join(SIGNAL_DIR, f"signal_{code}.txt")
                                if not os.path.exists(signal_path):
                                    with open(signal_path, 'w') as f:
                                        f.write(f"{signal},{code},1")
                                    print(f"!!! 주문 신호 생성: {signal} -> '{signal_path}'")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nAI 컨트롤러를 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_ai_controller()
