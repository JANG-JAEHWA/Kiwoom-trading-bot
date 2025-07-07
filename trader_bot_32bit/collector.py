import os
import time
from kiwoom_api import KiwoomAPI
from PyQt5.QtWidgets import QApplication
import sys
import pandas as pd
from datetime import datetime
from PyQt5.QtCore import QEventLoop, QTimer

class Collector:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.kiwoom = KiwoomAPI()
        self.event_loop = None 
        
        self.kiwoom.collection_done_signal.connect(self.on_collection_done)
        self.kiwoom.page_data_received_signal.connect(self.on_page_data_received)
        
        self.current_file_path = ""
        self.is_file_new = True
        self.collection_timed_out = False

    def on_page_data_received(self, data):
        if not data: return
        
        df_page = pd.DataFrame(data)
        if self.is_file_new:
            df_page.to_csv(self.current_file_path, index=False, encoding='utf-8-sig')
            self.is_file_new = False
        else:
            df_page.to_csv(self.current_file_path, mode='a', header=False, index=False, encoding='utf-8-sig')
        
        current_size = os.path.getsize(self.current_file_path) / (1024) # KB 단위
        print(f" -> {self.kiwoom.current_code}: {current_size:.0f} KB 수집 중...", end='\r')
        
    def on_collection_done(self):
        self.collection_timed_out = False
        if self.event_loop and self.event_loop.isRunning(): self.event_loop.exit()
        
    def on_timeout(self):
        print("\n[경고] 15초 이상 응답이 없어 다음 종목으로 넘어갑니다.")
        self.collection_timed_out = True
        if self.event_loop and self.event_loop.isRunning(): self.event_loop.exit()
        
    def run(self):
        self.kiwoom.login()

        data_dir = "C:/program trading system/data_3min"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        all_codes = self.kiwoom.get_code_list("0") + self.kiwoom.get_code_list("10")
        today_str = datetime.now().strftime('%Y%m%d')

        for i, code in enumerate(all_codes):
            print(f"\n[{i+1}/{len(all_codes)}] {code} 종목 처리 시작...")
            
            self.current_file_path = os.path.join(data_dir, f"{code}_3min_data.csv")
            self.is_file_new = not os.path.exists(self.current_file_path)
            if not self.is_file_new:
                print("-> 파일이 이미 존재하므로 건너뜁니다.")
                continue

            state = self.kiwoom.get_stock_state(code)
            if any(keyword in state for keyword in ["관리종목", "거래정지", "정리매매"]):
                print(f"-> '{state}' 상태이므로 수집에서 제외합니다.")
                continue

            self.collection_timed_out = True
            self.event_loop = QEventLoop()
            
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(self.on_timeout)
            timer.start(30000)

            self.kiwoom.start_collecting_minute_data(code)
            self.event_loop.exec_()
            timer.stop()

            if self.collection_timed_out: continue

            print(" " * 70, end="\r")
            today_str = datetime.now().strftime('%Y%m%d')
            df = pd.read_csv(self.current_file_path)
            df.drop_duplicates(inplace=True)
            df_past = df[df['date'].astype(str).str.slice(0, 8) != today_str].copy()
            df_past.sort_values(by='date', ascending=True, inplace=True)
            df_past.to_csv(self.current_file_path, index=False, encoding='utf-8-sig')
            print(f"-> {code} 과거 데이터 저장 및 정리 완료. (총 {len(df_past)}개)")
                
        print("\n\n모든 종목의 데이터 수집이 완료되었습니다.")
        self.app.quit()
            
if __name__ == "__main__":
    collector = Collector()
    collector.run()