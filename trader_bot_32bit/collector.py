import os
import time
from kiwoom_api import KiwoomAPI
from PyQt5.QtWidgets import QApplication
import sys
import pandas as pd

def collect_all_market_data():
    app = QApplication(sys.argv)
    kiwoom = KiwoomAPI()
    kiwoom.login()

    if not os.path.exists("data"):
        os.makedirs("data")
        print("'data' 폴더를 생성했습니다.")

    kospi_codes = kiwoom.get_code_list("0")
    kosdaq_codes = kiwoom.get_code_list("10")
    all_codes = kospi_codes + kosdaq_codes

    print(f"데이터 수집 대상 종목 수: {len(all_codes)}개")

    for i, code in enumerate(all_codes[:10]):
        print(f"[{i+1}/{len(all_codes)}] {code} 종목 데이터 수집 시작...")

        time.sleep(3.6)

        daily_data = kiwoom.get_daily_data(code, continuous=True)

        if daily_data and len(daily_data) > 0:
            df = pd.DataFrame(daily_data)
            df = df.sort_values(by='date', ascending=True)

            file_path = os.path.join("data", f"{code}_daily_data.csv")
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"-> {code} 데이터 저장 완료. (총 {len(df)}일치")
        else:
            print(f"-> {code} 데이터 수집 실패.")
    print("\n모든 종목의 데이터 수집이 완료되었습니다.")
    app.quit()
if __name__ == "__main__":
    collect_all_market_data()
