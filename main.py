import sys
from PyQt5.QtWidgets import QApplication
from kiwoom_api import KiwoomAPI

def main():
    print("자동매매 프로그램 시작")
    kiwoom = KiwoomAPI()
    kiwoom.login()
    print(f"로그인 후 확인된 계좌번호: {kiwoom.account_number}")
    print("프로그램의 첫 단계 완료")

if __name__ == "__main__":
    app = QApplication(sys.argv) #PyQt5 생성
    main()
    
