import pandas as pd, joblib, os, time, socket, json
from feature_engineering import generate_features
from datetime import datetime
import pandas_ta as ta
from threading import Thread, Lock

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
WATCHLIST_PATH = os.path.join(PROJECT_ROOT, "watchlist.txt")
UNIVERSAL_MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "universal_strategist_optimized.joblib")
CUSTOM_MODELS_DIR = os.path.join(PROJECT_ROOT, "models", "custom_stratgists")
LIVE_DIR_1MIN = os.path.join(PROJECT_ROOT, "data", "live_data_1min")
LIVE_DIR_3MIN = os.path.join(PROJECT_ROOT, "data", "live_data_3min")
HISTORICAL_DIR = os.path.join(PROJECT_ROOT, "data_3min")

positions = {}
data_lock = Lock()

try:
    UNIVERSAL_MODEL = joblib.load(UNIVERSAL_MODEL_PATH)
except FileNotFoundError:
    print(f"경고: 범용 AI 모델({UNIVERSAL_MODEL_PATH})을 찾을 수 없습니다.")
    UNIVERSAL_MODEL = None

def load_data(path):
    try: return pd.read_csv(path, dtype={'date': str})
    except (FileNotFoundError, pd.errors.EmptyDataError): return None

def get_signal(code, combined_df):
    if UNIVERSAL_MODEL is None:
        return "HOLD"
    
    features_df = generate_features(combined_df.copy())
    if features_df.empty: return "HOLD"
    features = [
    'volatility_1h', 'momentum_2h',
    'volatility_ratio', 'volume_weighted_momentum'
    ]
    latest_features = features_df[features].iloc[[-1]]
    if latest_features.isnull().values.any(): return "HOLD"
    
    proba = UNIVERSAL_MODEL.predict_proba(latest_features)[:, 1][0]
    print(f"-> [{code}] 범용 모델 판단 확률: {proba*100:.2f}%")
    return "BUY" if proba >= 0.5 else "HOLD"


def send_signal(signal, code, qty, client_socket):
    if signal in ["BUY", "SELL"]:
        try:
            message = f"{signal},{code},{qty}"
            client_socket.sendall(message.encode())
            print(f"!!![{code}] 주문 신호 전송: {signal} {qty}주 !!!")
        except Exception as e:
            print(f"소켓 메시지 전송 실패: {e}")

def monitor_trades(client_socket):
    print("--- 통합 거래 감시 스레드 시작 (1분봉 기준) ---")
    last_mod_times = {}
    while True:
        try:
            with open(WATCHLIST_PATH, 'r') as f: watchlist = [line.strip() for line in f.readlines() if line.strip()]
            codes_to_check = set(watchlist + list(positions.keys()))

            for code in codes_to_check:
                live_path = os.path.join(LIVE_DIR_3MIN, f"live_{code}.csv")
                if not os.path.exists(live_path): continue

                mod_time = os.path.getmtime(live_path)
                if mod_time == last_mod_times.get(code):
                    continue
                last_mod_times[code] = mod_time
                live_df = load_data(live_path)
                if live_df is None or live_df.empty: continue

                current_price = live_df['close'].iloc[-1]

                with data_lock:
                    if code in positions:
                        pos = positions[code]
                        take_profit_price = pos['entry_price'] * 1.015
                        stop_loss_price = pos['entry_price'] * 0.99
                        now_time_str = datetime.now().strftime('%H%M')
                        is_time_to_exit = now_time_str >= "1455"

                        if current_price >= take_profit_price or current_price <= stop_loss_price or is_time_to_exit:
                            reason = "익절" if current_price >= take_profit_price else ("손절" if current_price <= stop_loss_price else "장마감")
                            print(f"-> 청산 신호 ({reason}): [{code}] SELL")
                            send_signal("SELL", code, pos['qty'], client_socket)
                            del positions[code]
                    elif code in watchlist:
                        hist_df = load_data(os.path.join(HISTORICAL_DIR, f"{code}_3min_data.csv"))
                        if hist_df is None: continue

                        combined_df = pd.concat([hist_df, live_df]).drop_duplicates(subset=['date'], keep='last').reset_index(drop=True)
                        if len(combined_df) < 101: continue

                        signal = get_signal(code, combined_df)
                        if signal == "BUY":
                            buy_qty = int(1_000_000 / current_price)
                            if buy_qty > 0:
                                send_signal("BUY", code, buy_qty, client_socket)
                                positions[code] = {'qty': buy_qty, 'entry_price': current_price}
                                print(f"-> 포지션 기록 완료: {positions[code]}")
            time.sleep(5)
        except Exception as e:
                print(f"\n감시 스레드 오류: {e}")
                time.sleep(5)

def run_ai_controller():
    print("--- AI 컨트롤러 시작(실전 버전) ---")

    client_socket = None

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('127.0.0.1', 9999))
        print("GUI의 통신 서버에 성공적으로 접속했습니다.")
    except Exception as e:
        print(f"GUI 통신 서버 접속 실패: {e}")
        return

    try:
        with open(WATCHLIST_PATH, 'r') as f:
            watchlist = [line.strip() for line in f if line.strip()]
        
    except FileNotFoundError: print(f"{WATCHLIST_PATH}를 찾을 수 없습니다."); return

    trade_monitor_thread = Thread(target=monitor_trades, args=(client_socket,), daemon=True)
    trade_monitor_thread.start()
    trade_monitor_thread.join()

    if client_socket: 
        client_socket.close()

if __name__ == "__main__":
    run_ai_controller()
