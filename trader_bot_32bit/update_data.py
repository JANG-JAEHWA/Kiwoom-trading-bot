import os
import sys
import pandas as pd
from datetime import datetime
from kiwoom_api_collector import KiwoomAPI
from PyQt5.QtWidgets import QApplication
import time

def run_updater():
    app = QApplication(sys.argv)
    kiwoom = KiwoomAPI()
    kiwoom.login()

    data_dir = "C:/program trading system/data_3min"
    stock_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    
    for i, file_name in enumerate(stock_files):
        code = file_name.split('_')[0]
        file_path = os.path.join(data_dir, file_name)
        print(f"\n[{i+1}/{len(stock_files)}] {code} 종목 최신화 시작...")
        
        time.sleep(0.3)
        new_data, _ = kiwoom.get_minute_data_page(code)

        if not new_data:
            print(f"-> 최신 데이터 없음. 건너뜁니다.")
            continue
        
        existing_df = pd.read_csv(file_path, dtype={'date': str})
        new_df = pd.DataFrame(new_data)
        combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['date'], keep='last')
        combined_df = combined_df.sort_values(by='date', ascending=True)
        
        combined_df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print(f"-> 데이터 최신화 완료. (총 {len(new_df)}개)")

    print("\n\n모든 종목 데이터 최신화 완료.")
    app.quit()

if __name__ == "__main__":
    run_updater()