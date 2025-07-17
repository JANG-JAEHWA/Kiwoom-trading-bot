import os
import sys
import pandas as pd
from datetime import datetime

from kiwoom_api_collector import KiwoomAPICollector
from PyQt5.QtWidgets import QApplication
import time

def run_updater():
    app = QApplication(sys.argv)
    kiwoom = KiwoomAPICollector()
    if kiwoom.get_connect_state() == 0:
        kiwoom.login()

    data_dir = "C:/program trading system/data_3min"
    stock_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    
    for i, file_name in enumerate(stock_files):
        code = file_name.split('_')[0]
        file_path = os.path.join(data_dir, file_name)
        print(f"\n[{i+1}/{len(stock_files)}] {code} 종목 최신화 시작...")
        
        try:
            existing_df = pd.read_csv(file_path, dtype={'date': str})
            existing_dates = set(existing_df['date'])
        except Exception as e:
            print(f"-> 파일 읽기 오류: {e}"); continue
        
        all_new_data = []
        is_gap_bridged = False
        is_first_page = True

        while True:
            time.sleep(0.3)
            page_data, prev_next = kiwoom.get_minute_data_page(code, is_continuous=not is_first_page)
            is_first_page = False

            if not page_data: break
            
            new_unique_data = []
            for item in page_data:
                if str(item['date']) in existing_dates:
                    is_gap_bridged = True
                    break
                new_unique_data.append(item)

            if new_unique_data:
                all_new_data.extend(new_unique_data)
                print(f"-> 누락된 데이터 {len(all_new_data)}개 추가 수집...", end='\r')
            if is_gap_bridged or prev_next != "2":
                break
        

        if all_new_data:
            print(" " * 70, end='\r')
            new_df = pd.DataFrame(all_new_data)
            combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['date'], keep='last')
            combined_df = combined_df.sort_values(by='date', ascending=True)
        
            combined_df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"-> 데이터 최신화 완료. ({len(all_new_data)}개 추가, 총 {len(combined_df)}개)")
        else:
            print("-> 추가할 최신 데이터가 없습니다.")

    print("\n\n모든 종목 데이터 최신화 완료.")
    app.quit()

if __name__ == "__main__":
    run_updater()