import pandas as pd
from feature_engineering import generate_features
import joblib
import os
import time
import socket

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
WATCHLIST_PATH = os.path.join(PROJECT_ROOT, "watchlist.txt")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "strategist_model_daily.joblib")
LIVE_DIR = os.path.join(PROJECT_ROOT, "data", "live_data")
HISTORICAL_DIR = os.path.join(PROJECT_ROOT, "data_3min")

def load_data(path, dtype=None):
    try: return pd.read_csv(path, dtype=dtype)
    except (FileNotFoundError, pd.errors.EmptyDataError): return None

def make_prediction(model, combined_df):
    features_df = generate_features(combined_df.copy())
    if len(features_df) < 1: return "HOLD"
    features = ['volatility_1h', 'momentum_2h', 'volume_ratio', 'atr', 'roc', 'volatility_of_volatility', 'momentum_acceleration', 'vp_corr_1h']
    latest_features = features_df[features].iloc[[-1]]
    if latest_features.isnull().values.any(): return "HOLD"
    prediction = model.predict(latest_features)
    if prediction[0] == 1: return "BUY"
    return "HOLD"

def write_signal(signal, code, client_socket):
    if signal == "BUY":
        try:
            message = f"BUY,{code},10"
            client_socket.sendall(message.encode())
            print(f"!!! 주문 신호 전송: {message}")
        except Exception as e:
            print(f"소켓 메시지 전송 실패: {e}")
        


def run_ai_controller():
    print("--- AI 컨트롤러 시작(소켓 버전) ---")

    server_ip = '127.0.0.1'
    server_port = 9999
    client_socket = None

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server_ip, server_port))
        print("GUI의 통신 서버에 성공적으로 접속했습니다.")
    except Exception as e:
        print(f"GUI 통신 서버 접속 실패: {e}")

    try:
        strategist_model = joblib.load(MODEL_PATH)
        print("AI 전략가 모델을 성공적으로 불러왔습니다.")
    except FileNotFoundError:
        print(f"AI 모델을 찾을 수 없습니다: {MODEL_PATH}")
        if client_socket: client_socket.close()
        return
    
    if not os.path.exists(LIVE_DIR): os.makedirs(LIVE_DIR)

    last_mod_times = {}
    while True:
        try:
            with open(WATCHLIST_PATH, 'r') as f: watchlist = [line.strip() for line in f.readlines() if line.strip()]
            if not watchlist: 
                time.sleep(10)
                continue

            for code in watchlist:
                live_path = os.path.join(LIVE_DIR, f"live_{code}.csv")
                if not os.path.exists(live_path): continue
                
                mod_time = os.path.getmtime(live_path)
                if mod_time != last_mod_times.get(code):
                    last_mod_times[code] = mod_time
                    print(f"\n[{code}] 새 데이터 감지. 분석 시작...")
                    
                    hist_df = load_data(os.path.join(HISTORICAL_DIR, f"{code}_3min_data.csv"), dtype={'date': 'str'})
                    live_df = load_data(live_path, dtype={'date': 'str'})
                    if hist_df is None or live_df is None: continue
                    
                    combined_df = pd.concat([hist_df, live_df]).drop_duplicates(['date'], keep='last')
                    if len(combined_df) > 100:
                        signal = make_prediction(strategist_model, combined_df)
                        print(f"-> AI 판단: [{code}] {signal}")
                        write_signal(signal, code, client_socket)
            time.sleep(3)
        except (BrokenPipeError, ConnectionResetError):
            print("GUI와의 연결이 끊어졌습니다. 컨트롤러를 종료합니다.")
            break
        except Exception as e: print(f"\n컨트롤러 오류: {e}"); time.sleep(3)
    if client_socket: client_socket.close()
def main():
    run_ai_controller()
if __name__ == "__main__":
    main()
