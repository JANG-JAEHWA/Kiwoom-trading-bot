import os
import pandas as pd
import sys
from PyQt5.QtWidgets import QApplication
from kiwoom_api import KiwoomAPI
from strategy import simple_ma_strategy

def main():
    print("AI 트레이딩 시스템 - 데이터 수집기 시작")
    
    
    kiwoom = KiwoomAPI()
    kiwoom.login()
    print(f"로그인 후 확인된 계좌번호: {kiwoom.account_number}")

    if not os.path.exists("data"):
        os.makedirs("data")
        print("'data'폴더를 생성했습니다.")
    
    samsung_data = kiwoom.get_daily_data("005930", continuous=True)

    if samsung_data:
        df = pd.DataFrame(samsung_data)
        df = df.sort_values(by='date', ascending=True)

        file_path = os.path.join("data", "005930_daily_data.csv")

        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print(f"데이터를 성공적으로 저장했습니다: {file_path}")
    else:
        print("데이터를 가져오는 데 실패했습니다.")
    print("\n모든 테스트가 완료되었습니다.")

if __name__ == "__main__":
    app = QApplication(sys.argv) #PyQt5 생성
    main()
    
