from kiwoom_api import KiwoomAPI
from PyQt5.QtWidgets import QApplication
import sys

def run_realtime_trader(code="005930"):
    app = QApplication(sys.argv)
    kiwoom = KiwoomAPI()
    kiwoom.login()
    
    kiwoom.subscribe_realtime_data("0101", code, "20;10;15", "0")

    print(f"\n[{code}] 종목에 대한 실시간 데이터 수신을 시작합니다...")
    print("프로그램을 종료하려면 터미널에서 Ctrl+C를 누르세요.")

    app.exec_()

    
if __name__ == "__main__":
    run_realtime_trader()