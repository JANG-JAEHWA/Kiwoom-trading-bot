import pandas as pd, joblib, os, time, socket, json
from feature_engineering import generate_features
from datetime import datetime
import pandas_ta as ta
from threading import Thread, Lock

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
WATCHLIST_PATH = os.path.join(PROJECT_ROOT, "watchlist.txt")
UNIVERSAL_MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "strategist_model_v1.joblib")
CUSTOM_MODELS_DIR = os.path.join(PROJECT_ROOT, "models", "custom_stratgists")
RULES_PATH = os.path.join(PROJECT_ROOT, "rules", "optimal_rules.json")
LIVE_DIR_1MIN = os.path.join(PROJECT_ROOT, "data", "live_data_1min")
LIVE_DIR_3MIN = os.path.join(PROJECT_ROOT, "data", "live_data_3min")
HISTORICAL_DIR = os.path.join(PROJECT_ROOT, "data_3min")

positions = {}
stock_states = {}
optimal_rules = {}
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
    features_df = generate_features(combined_df.copy())
    if features_df.empty: return "HOLD"
    features = ['volatility_1h', 'momentum_2h', 'volume_ratio', 'atr', 'roc', 'volatility_of_volatility', 'momentum_acceleration', 'vp_corr_1h']
    latest_features = features_df[features].iloc[[-1]]
    if latest_features.isnull().values.any(): return "HOLD"

    # 맞춤형 모델 예측
    try:
        custom_model = joblib.load(os.path.join(CUSTOM_MODELS_DIR, f"strategist_{code}.joblib"))
        custom_proba = custom_model.predict_proba(latest_features)[:, 1][0]
        print(f"-> [{code}] 맞춤형 모델 판단: {custom_proba*100:.2f}%")
        if custom_proba >= 0.5: return "BUY"
    except FileNotFoundError: pass

    # 범용 모델 예측
    if UNIVERSAL_MODEL:
        universal_proba = UNIVERSAL_MODEL.predict_proba(latest_features)[:, 1][0]
        print(f"-> [{code}] 범용 모델 판단: {universal_proba*100:.2f}%")
        if universal_proba >= 0.5: return "BUY"
            
    return "HOLD"


def send_signal(signal, code, qty, client_socket):
    if signal in ["BUY", "SELL"]:
        try:
            message = f"{signal},{code},{qty}"
            client_socket.sendall(message.encode())
            print(f"!!![{code}] 주문 신호 전송: {signal} {qty}주 !!!")
        except Exception as e:
            print(f"소켓 메시지 전송 실패: {e}")

def monitor_for_entry(client_socket):
    print("--- 진입 감시 스레드 시작 (3분봉 기준) ---")
    last_mod_times = {}
    while True:
        try:
            with open(WATCHLIST_PATH, 'r') as f: watchlist = [line.strip() for line in f.readlines() if line.strip()]
            if not watchlist: 
                time.sleep(5)
                continue
            for code in watchlist:
                if code in positions: continue
                with data_lock:
                    if stock_states.get(code, {}).get('status') != 'WATCHING' : continue

                live_path = os.path.join(LIVE_DIR_3MIN, f"live_{code}.csv")
                if not os.path.exists(live_path): continue
                
                mod_time = os.path.getmtime(live_path)
                if mod_time == last_mod_times.get(code):
                    continue
                last_mod_times[code] = mod_time
                print(f"\n[{code}] 새 3분봉 감지 (진입 조건 분석)...")
                    
                hist_df = load_data(os.path.join(HISTORICAL_DIR, f"{code}_3min_data.csv"))
                live_df = load_data(live_path)
                if hist_df is None or live_df is None: continue
                    
                combined_df = pd.concat([hist_df, live_df]).drop_duplicates(subset=['date'], keep='last').reset_index(drop=True)
                if len(combined_df) < 101: continue

                signal = get_signal(code, combined_df)
                print(f"-> AI 판단 (3분봉): [{code}] {signal}")

                if signal == "BUY":
                    with data_lock:
                        stock_states[code]['status'] = 'ENTRY_WINDOW_OPEN'
                        stock_states[code]['window_expires_at'] = time.time() + 180
                    print(f"*** [{code}] 공격 허가! 3분간 정밀 타격 기회 탐색. ***")
            time.sleep(10)
        except Exception as e: print(f"\n진입 감시 오류: {e}"); time.sleep(10)

def monitor_for_execution(client_socket):
    global stock_states, positions
    print("--- 실행/청산 감시 스레드 시작 (1분봉 기준) ---")
    last_mod_times = {}

    while True:
        try:
            codes_to_check = list(stock_states.keys())
            for code in codes_to_check:
                live_path = os.path.join(LIVE_DIR_1MIN, f"live_{code}.csv")
                if not os.path.exists(live_path): continue
                
                mod_time = os.path.getmtime(live_path)
                if mod_time == last_mod_times.get(code): continue
                
                last_mod_times[code] = mod_time
                live_df = load_data(live_path)
                if live_df is None or live_df.empty: continue
                
                current_price = live_df['close'].iloc[-1]

                with data_lock:
                    state_info = stock_states.get(code, {})
                    status = state_info.get('status')

                    if status == 'IN_POSITION':
                        pos = positions.get(code)
                        if not pos: continue
                        live_df['atr'] = ta.atr(live_df['high'], live_df['low'], live_df['close'], length=14)
                        current_atr = live_df['atr'].iloc[-1]
                        if pd.isna(current_atr) or current_atr == 0: continue
                        atr_multiplier = optimal_rules.get(code, {}).get('atr_multiplier', 2.5)
                        pos['highest_price'] = max(pos['highest_price'], current_price)
                        pos['stop_loss_price'] = max(pos.get('stop_loss_price', 0), pos['highest_price'] - (current_atr * atr_multiplier))
                        now_time_str = datetime.now().strftime('%H%M')
                        is_time_to_exit = now_time_str >= "1520"
                        if current_price < pos['stop_loss_price'] or is_time_to_exit:
                            print(f"-> 청산 신호 (1분봉): [{code}] SELL")
                            send_signal("SELL", code, pos['qty'], client_socket)
                            if code in positions: del positions[code]
                            state_info['status'] = 'WATCHING'

                    elif status == 'ENTRY_WINDOW_OPEN':
                        if time.time() > state_info.get('window_expires_at', 0):
                            print(f"[{code}] 공격 시간 초과. 정찰 모드로 복귀.")
                            state_info['status'] = 'WATCHING'; continue
                        
                        print(f"-> 정밀 타격 실행 (1분봉): [{code}] BUY")
                        buy_qty = int(1_000_000 / current_price)
                        if buy_qty > 0:
                            send_signal("BUY", code, buy_qty, client_socket)
                            state_info['status'] = 'IN_POSITION'
                            hist_df = load_data(os.path.join(HISTORICAL_DIR, f"{code}_3min_data.csv"))
                            combined_df = pd.concat([hist_df, live_df]).drop_duplicates(['date'], keep='last').reset_index(drop=True)
                            current_atr = ta.atr(combined_df['high'], combined_df['low'], combined_df['close'], length=14).iloc[-1]
                            atr_multiplier = optimal_rules.get(code, {}).get('atr_multiplier', 2.5)
                            positions[code] = {'qty': buy_qty, 'entry_price': current_price, 'highest_price': current_price, 'stop_loss_price': current_price - (current_atr * atr_multiplier)}
            time.sleep(1)
        except Exception as e: print(f"\n실행/청산 감시 오류: {e}"); time.sleep(1)
        
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

    global optimal_rules
    try:
        with open(RULES_PATH, 'r') as f: optimal_rules = json.load(f)
        print("종목별 최적 청산 규칙을 성공적으로 불러왔습니다.")
    except FileNotFoundError: print(f"경고: 최적 규칙 파일({RULES_PATH})을 찾을 수 없습니다.")

    global stock_states
    try:
        with open(WATCHLIST_PATH, 'r') as f:
            watchlist = [line.strip() for line in f if line.strip()]
        for code in watchlist:
            stock_states[code] = {'status': 'WATCHING'}
        print(f"초기 감시 대상 설정: {list(stock_states.keys())}")
    except FileNotFoundError: print(f"{WATCHLIST_PATH}를 찾을 수 없습니다."); return

    entry_thread = Thread(target=monitor_for_entry, args=(client_socket,), daemon=True)
    exit_thread = Thread(target=monitor_for_execution, args=(client_socket,), daemon=True)

    entry_thread.start()
    exit_thread.start()

    entry_thread.join()
    exit_thread.join()

if __name__ == "__main__":
    run_ai_controller()
