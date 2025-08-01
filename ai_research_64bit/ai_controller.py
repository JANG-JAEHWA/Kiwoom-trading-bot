import pandas as pd, joblib, os, time, socket, json
from feature_engineering import generate_features
from datetime import datetime
from threading import Thread, Lock
from collections import deque

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
WATCHLIST_PATH = os.path.join(PROJECT_ROOT, "watchlist.txt")
UNIVERSAL_MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "universal_strategist_optimized.joblib")
LIVE_DIR_1MIN = os.path.join(PROJECT_ROOT, "data", "live_data_1min")
LIVE_DIR_3MIN = os.path.join(PROJECT_ROOT, "data", "live_data_3min")
HISTORICAL_DIR = os.path.join(PROJECT_ROOT, "data_3min")

positions = {}
stock_states = {}
latest_orderbook = {}
data_lock = Lock()
latest_trades = {}

try:
    UNIVERSAL_MODEL = joblib.load(UNIVERSAL_MODEL_PATH)
except FileNotFoundError:
    print(f"경고: 범용 AI 모델({UNIVERSAL_MODEL_PATH})을 찾을 수 없습니다.")
    UNIVERSAL_MODEL = None

class OrderbookClientThread(Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.is_running = True
    
    def run(self):
        while self.is_running:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('127.0.0.1', 9998))
                    print("[Orderbook Client] GUI 호가 서버 접속 성공.")
                    while self.is_running:
                        data = s.recv(4096).decode('utf-8')
                        if not data: break
                        buffer += data
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            try:
                                orderbook = json.loads(line)
                                with data_lock:
                                    latest_orderbook[orderbook['code']] = orderbook
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                print(f"[Orderbook Client] 연결 오류: {e}. 5초 후 재시도.")
                time.sleep(5)
    def stop(self): self.is_running = False


def get_micro_price(orderbook):

    total_bid_value, total_bid_qty = 0, 0
    total_ask_value, total_ask_qty = 0, 0

    for i in range(1, 6):
        bid_price = orderbook.get(f'buy_price_{i}', 0)
        bid_qty = orderbook.get(f'buy_qty_{i}', 0)
        ask_price = orderbook.get(f'sell_price_{i}', 0)
        ask_qty = orderbook.get(f'sell_qty_{i}', 0)

        if bid_price * bid_qty * ask_price * ask_qty == 0: continue

        total_bid_value += bid_price * bid_qty
        total_ask_qty += bid_qty
        total_ask_value += ask_price * ask_qty
        total_ask_qty += ask_qty
    
    if total_bid_qty == 0 or total_ask_qty == 0:
        return None
    
    w_avg_bid = total_bid_value / total_bid_qty
    w_avg_ask = total_ask_value / total_ask_qty

    micro_price = (w_avg_bid * total_ask_qty + w_avg_ask * total_bid_qty) / (total_bid_qty + total_ask_qty)

    return micro_price

def get_orderbook_imbalance(orderbook):
    total_bid_qty = sum(orderbook.get(f'buy_qty_{i}', 0) for i in range(1, 6))
    total_ask_qty = sum(orderbook.get(f'sell_qty_{i}', 0) for i in range(1, 6))

    if (total_bid_qty + total_ask_qty) == 0:
        return None
    
    return total_bid_qty / (total_bid_qty + total_ask_qty)



def load_data(path):
    try: return pd.read_csv(path, dtype={'date': str})
    except (FileNotFoundError, pd.errors.EmptyDataError): return None

def get_entry_signal(code, combined_df):
    if UNIVERSAL_MODEL is None:
        return "HOLD"
    
    features_df = generate_features(combined_df.copy())
    if features_df.empty: return "HOLD"

    latest_data = features_df.iloc[-1]
    is_trending = latest_data.get('is_strong_trend', 0) == 1

    if not is_trending:
        print(f"-> [{code}] 정배열 조건 불충족. 매수 보류.")
        return "HOLD"
    
    print(f"-> [{code}] 정배열 조건 충족! AI 모델 분석 시작...")
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
    if signal in ["BUY", "SELL"] and client_socket:
        try:
            message = f"{signal},{code},{qty}"; client_socket.sendall(message.encode())
            print(f"!!! [{code}] 주문 신호 전송: {signal} {qty}주 !!!")
        except Exception as e: print(f"소켓 메시지 전송 실패: {e}")

def monitor_for_entry(client_socket):
    """(정찰팀) 3분봉을 감시하며 '공격 허가'를 내립니다."""
    last_mod_times = {}
    while True:
        try:
            with open(WATCHLIST_PATH, 'r') as f: watchlist = [line.strip() for line in f if line.strip()]
            if not watchlist: time.sleep(5); continue
            for code in watchlist:
                with data_lock:
                    if stock_states.get(code, {}).get('status') != 'WATCHING': continue
                
                live_path = os.path.join(LIVE_DIR_3MIN, f"live_{code}.csv")
                if not os.path.exists(live_path): continue
                mod_time = os.path.getmtime(live_path)
                if mod_time == last_mod_times.get(code): continue
                last_mod_times[code] = mod_time; print(f"\n[{code}] 3분봉 감지 (진입 분석)...")
                
                hist_df = load_data(os.path.join(HISTORICAL_DIR, f"{code}_3min_data.csv"))
                live_df = load_data(live_path)
                if hist_df is None or live_df is None: continue
                
                combined_df = pd.concat([hist_df, live_df]).drop_duplicates(subset=['date'], keep='last').reset_index(drop=True)
                if len(combined_df) > 100:
                    signal = get_entry_signal(code, combined_df)
                    if signal == "BUY":
                        with data_lock:
                            stock_states[code]['status'] = 'ENTRY_WINDOW_OPEN'; stock_states[code]['window_expires_at'] = time.time() + 180
                        print(f"*** [{code}] 공격 허가! 3분간 정밀 타격 기회 탐색. ***")
            time.sleep(10)
        except Exception as e: print(f"\n진입 감시 오류: {e}"); time.sleep(10)

def monitor_for_execution(client_socket):
    """(저격팀) 실시간 호가창을 보며 '정밀 타격(매수)'과 '신속한 청산(매도)'을 실행합니다."""
    print("--- 실행/청산 감시 스레드 시작 (실시간 호가 기준) ---")

    recent_obi = {code: deque(maxlen=3) for code in stock_states.keys()}
    recent_micro_price = {code: deque(maxlen=3) for code in stock_states.keys()}

    while True:
        try:
            with data_lock: codes_to_check = list(stock_states.keys())
            for code in codes_to_check:
                orderbook = latest_orderbook.get(code)
                if not orderbook: continue

                current_price = orderbook['buy_price_1']
                if current_price == 0: continue
                
                with data_lock:
                    state_info = stock_states.get(code, {})
                    status = state_info.get('status')
                    if status == 'IN_POSITION':
                        pos = positions.get(code)
                        if not pos: continue
                        take_profit_price = pos['entry_price'] * 1.015
                        stop_loss_price = pos['entry_price'] * 0.99
                        now_time_str = datetime.now().strftime('%H%M')
                        is_time_to_exit = now_time_str >= "1455"

                        live_df_1min = load_data(os.path.join(LIVE_DIR_1MIN, f"live_{code}.csv"))
                        is_vi_approaching = False
                        if live_df_1min is not None and not live_df_1min.empty:
                            latest_candle = live_df_1min.iloc[-1]
                            vi_static_price = latest_candle.get('vi_static_price', 0)
                            vi_dynamic_price = latest_candle.get('vi_dynamic_price', 0)
                            if vi_static_price > 0 and (current_price >= vi_static_price * 0.99): is_vi_approaching = True
                            if vi_dynamic_price > 0 and (current_price >= vi_dynamic_price * 0.99): is_vi_approaching = True
                        
                        if current_price >= take_profit_price or current_price <= stop_loss_price or is_time_to_exit or is_vi_approaching:
                            reason = "익절" if current_price >= take_profit_price else ("손절" if current_price <= stop_loss_price else ("VI임박" if is_vi_approaching else "장마감"))
                            print(f"-> 청산 신호 ({reason}): [{code}] SELL")
                            send_signal("SELL", code, pos['qty'], client_socket); del positions[code]; state_info['status'] = 'WATCHING'
                    elif status == 'ENTRY_WINDOW_OPEN':
                        if time.time() > state_info.get('window_expires_at', 0):
                            print(f"[{code}] 공격 시간 초과. 정찰 모드로 복귀.")
                            state_info['status'] = 'WATCHING'; continue
                        
                        micro_price = get_micro_price(orderbook)
                        if micro_price is None: continue
                        recent_micro_price[code].append(micro_price)

                        if len(recent_micro_price[code]) < 3: continue
                        is_micro_price_rising = (recent_micro_price[code][2] > recent_micro_price[code][1] > recent_micro_price[code][0])

                        obi = get_orderbook_imbalance(orderbook)
                        if obi is None: continue
                        recent_obi[code].append(obi)

                        if len(recent_obi[code]) < 3: continue
                        is_obi_tilting_to_buy = (recent_obi[code][2] > recent_obi[code][1] > recent_obi[code][0])

                        if is_micro_price_rising and is_obi_tilting_to_buy and obi > 0.6:
                            print(f"-> 정밀 타격 신호 포착 (Micro-price 상승 & OBI 매수 쏠림): [{code}] BUY")
                            buy_qty = int(1_000_000 / current_price)
                            if buy_qty > 0:
                                send_signal("BUY", code, buy_qty, client_socket)
                                state_info['status'] = 'IN_POSITION'
                                positions[code] = {'qty': buy_qty, 'entry_price': current_price}
            time.sleep(0.5)
        except Exception as e: print(f"\n실행/청산 감시 오류: {e}"); time.sleep(1)

def main():
    global stock_states
    client_socket = None
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM); client_socket.connect(('127.0.0.1', 9999))
        print("GUI 주문 서버 접속 성공.")
    except Exception as e: print(f"GUI 주문 서버 접속 실패: {e}"); return
    
    try:
        with open(WATCHLIST_PATH, 'r') as f: codes = [line.strip() for line in f if line.strip()]
        for code in codes: stock_states[code] = {'status': 'WATCHING'}
        print(f"초기 감시 대상: {list(stock_states.keys())}")
    except FileNotFoundError: print(f"{WATCHLIST_PATH} 없음."); client_socket.close(); return
    
    orderbook_client = OrderbookClientThread(); orderbook_client.start()
    entry_thread = Thread(target=monitor_for_entry, args=(client_socket,), daemon=True); entry_thread.start()
    execution_thread = Thread(target=monitor_for_execution, args=(client_socket,), daemon=True); execution_thread.start()
    print("--- AI 컨트롤러 시작 (v2.0 하이브리드) ---")
    
    entry_thread.join(); execution_thread.join()
    if client_socket: client_socket.close()


if __name__ == "__main__":
    main()
