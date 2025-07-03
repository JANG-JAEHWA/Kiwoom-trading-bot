from kiwoom_api import KiwoomAPI
from PyQt5.QtWidgets import QApplication
import sys
import time
import pandas as pd
import os

LIVE_DATA_PATH = "../data/live_data.csv"
SIGNAL_PATH = "../signal.txt"

class RealtimeTrader:
    def __init__(self, code="005930"):
        self.code = code
        self.app = QApplication(sys.argv)
        self.kiwoom = KiwoomAPI()
        self.kiwoom.login()
    
    def run(self):
        self.kiwoom.subscribe_realtime_data("0101", self.code, "20;10;15", "0")

        print(f"\n[{self.code}] 종목에 대한 실시간 데이터 수신을 시작합니다...")
        print("프로그램을 종료하려면 터미널에서 Ctrl+C를 누르세요.")

        while True:
            QApplication.processEvents()
            self.check_signal()
            time.sleep(3)
    
    def on_candle_completed(self, candle_data):
        """3분봉 캔들 완성후 호출 함수"""
        print("\n--- [3분봉 완성] ---")
        print(candle_data)

        df = pd.DataFrame([candle_data])
        df.to_csv(LIVE_DATA_PATH, index=False, encoding='utf-8-sig')
        print(f"'{LIVE_DATA_PATH}'에 최신 캔들 데이터를 저장했습니다.")
        print("--------------------") 

    def check_signal(self):
        if os.path.exists(SIGNAL_PATH):
            print("[!!] 주문 신호 감지!")
            with open(SIGNAL_PATH, 'r') as f:
                content = f.read().strip()
            
            parts = content.split(',')
            if len(parts) == 3:
                order_type, code, qty = parts
                qty = int(qty)

                if order_type.upper() == "BUY":
                    self.kiwoom.send_order(
                        rqname=f"{code}_매수", screen_no="0103", acc_no=self.kiwoom.account_number,
                        order_type=1, code=code, qty=qty, price=0, hoga_gb="03", org_order_no=""
                    )
                elif order_type.upper() == "SELL":
                    self.kiwoom.send_order(
                        rqname=f"{code}_매도", screen_no="0104", acc_no=self.kiwoom.account_number,
                        order_type=2, code=code, qty=qty, price=0, hoga_gb="03", org_order_no=""
                    )
            os.remove(SIGNAL_PATH)
            print(f"신호 파일을 처리하고 '{SIGNAL_PATH}'를 삭제했습니다.")

if __name__ == "__main__":
    KiwoomAPI.on_candle_completed = RealtimeTrader.on_candle_completed
    trader = RealtimeTrader()
    trader.run()