import os
import time
from kiwoom_api import KiwoomAPI
from PyQt5.QtWidgets import QApplication
import sys
import pandas as pd
from datetime import datetime

def collect_all_minute_data():
    app = QApplication(sys.argv)
    kiwoom = KiwoomAPI()
    kiwoom.login()
    kiwoom.unsubscribe_realtime_data()

    data_dir = "C:/program trading system/data_3min"

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"'{data_dir}' 폴더를 생성했습니다.")

    kospi_codes = kiwoom.get_code_list("0")
    kosdaq_codes = kiwoom.get_code_list("10")
    all_codes = kospi_codes + kosdaq_codes

    print(f"데이터 수집 대상 종목 수: {len(all_codes)}개")

    today_str = datetime.now().strftime('%Y%m%d')

    for i, code in enumerate(all_codes):
        print(f"[{i+1}/{len(all_codes)}] {code} 종목 데이터 수집 시작...")

        time.sleep(1)

        minute_data = kiwoom.get_minute_data(code, tick_range=3, continuous=True)

        if minute_data and len(minute_data) > 0:
            df = pd.DataFrame(minute_data)
            df_past = df[df['date'].str.slice(0, 8) != today_str].copy()
            if df_past.empty:
                continue
            df_past = df.sort_values(by='date', ascending=True)

            file_path = os.path.join(data_dir, f"{code}_3min_data.csv")
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"-> {code} 데이터 저장 완료. (총 {len(df_past)}개)")
        else:
            print(f"-> {code} 데이터 수집 실패.")
    print("\n모든 종목의 데이터 수집이 완료되었습니다.")
    app.quit()
if __name__ == "__main__":
    collect_all_minute_data()
