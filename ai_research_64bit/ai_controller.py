import pandas as pd, joblib, os, time, socket
from feature_engineering import generate_features
from datetime import datetime
import pandas_ta as ta

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
WATCHLIST_PATH = os.path.join(PROJECT_ROOT, "watchlist.txt")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "strategist_model_daily.joblib")
LIVE_DIR = os.path.join(PROJECT_ROOT, "data", "live_data")
HISTORICAL_DIR = os.path.join(PROJECT_ROOT, "data_3min")

positions = []

def load_data(path):
    try: return pd.read_csv(path, dtype={'date': str})
    except (FileNotFoundError, pd.errors.EmptyDataError): return None

def get_signal(model, combined_df):
    features_df = generate_features(combined_df.copy())
    if len(features_df) < 1: return "HOLD"
    features = ['volatility_1h', 'momentum_2h', 'volume_ratio', 'atr', 'roc', 'volatility_of_volatility', 'momentum_acceleration', 'vp_corr_1h']
    latest_features = features_df[features].iloc[[-1]]
    if latest_features.isnull().values.any(): return "HOLD"
    prediction = model.predict(latest_features)
    if prediction[0] == 1: return "BUY"
    return "HOLD"

def send_signal(signal, code, qty, client_socket):
    if signal == ["BUY", "SELL"]:
        try:
            message = f"{signal},{code},{qty}"
            client_socket.sendall(message.encode())
            print(f"!!![{code}] 주문 신호 전송: {signal} {qty}주 !!!")
        except Exception as e:
            print(f"소켓 메시지 전송 실패: {e}")
        


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
        model = joblib.load(MODEL_PATH)
        print("AI 전략가 모델을 성공적으로 불러왔습니다.")
    except FileNotFoundError:
        print(f"AI 모델을 찾을 수 없습니다: {MODEL_PATH}")
        client_socket.close()
        return
    
    if not os.path.exists(LIVE_DIR): os.makedirs(LIVE_DIR)

    last_mod_times = {}
    while True:
        try:
            with open(WATCHLIST_PATH, 'r') as f: watchlist = [line.strip() for line in f.readlines() if line.strip()]
            if not watchlist: 
                time.sleep(5)
                continue

            for code in watchlist:
                live_path = os.path.join(LIVE_DIR, f"live_{code}.csv")
                if not os.path.exists(live_path): continue
                
                mod_time = os.path.getmtime(live_path)
                if mod_time == last_mod_times.get(code):
                    continue
                last_mod_times[code] = mod_time
                print(f"\n[{code}] 새 데이터 감지. 분석 시작...")
                    
                hist_df = load_data(os.path.join(HISTORICAL_DIR, f"{code}_3min_data.csv"))
                live_df = load_data(live_path)
                if hist_df is None or live_df is None: continue
                    
                combined_df = pd.concat([hist_df, live_df]).drop_duplicates(['date'], keep='last')
                if len(combined_df) < 101: continue

                current_price = combined_df['close'].iloc[-1]

                if code in positions:
                    pos = positions[code]
                    currnet_atr = ta.atr(combined_df['high'], combined_df['low'], combined_df['close'], length=14).iloc[-1]

                    pos['highest_price'] = max(pos['highest_price'], current_price)
                    trailing_stop_price = pos['highest_price'] - (currnet_atr * 2.5) # ATR 2.5배수
                    pos['stop_loss_price'] = max(pos['stop_loss_price'], trailing_stop_price)

                    is_time_to_exit = datetime.now().hour == 15 and datetime.now().minute >= 20

                    if current_price < pos['stop_loss_price'] or is_time_to_exit:
                        print(f"-> AI 판단: [{code}] SELL (청산)")
                        send_signal("SELL", code, pos['qty'], client_socket)
                        del positions[code]
                else:
                    signal = get_signal(model, combined_df)
                    print(f"-> AI 판단: [{code}] {signal}")
                    if signal == "BUY":
                        trade_capital = 1_000_000
                        buy_qty = int(trade_capital / current_price)
                        if buy_qty == 0:
                            print(f"-> [{code}] 주가가 높아, 최소 1주도 매수할 수 없습니다.")
                            continue
                        send_signal("buy", code, buy_qty, client_socket)
                        currnet_atr = ta.atr(combined_df['high'], combined_df['low'], combined_df['close'], length=14).iloc[-1]
                        positions[code] = {'entry_price': current_price, 'qty': buy_qty, 'highest_price': current_price, 'stop_loss_price': current_price - (current_price * 2.5)}
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
