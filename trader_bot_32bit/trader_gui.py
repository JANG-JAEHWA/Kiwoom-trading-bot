import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QPushButton, QTextEdit, QLabel, QLineEdit, QHBoxLayout)
from PyQt5.QtCore import  QThread, pyqtSignal, QTimer, QDateTime
from kiwoom_api import KiwoomAPI
import pandas as pd
import socket
import csv
from datetime import datetime

class SignalServerThread(QThread):
    order_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_running = True
    
    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.bind(('127.0.0.1', 9999))
                server_socket.listen()
                print("[Signal Server] AI 컨트롤러의 접속을 기다립나다...")
                conn, addr = server_socket.accept()
                with conn:
                    print(f"[Signal_Server] AI 컨트롤러의 접속: {addr}")
                    while self.is_running:
                        data = conn.recv(1024)
                        if not data:
                            break
                        message = data.decode()
                        self.order_signal.emit(message)
        except Exception as e:
            print(f"[Signal Server] 오류 발생: {e}")
        
    def stop(self):
        self.is_running = False


class KiwoomWorker(QThread):
    def __init__(self, kiwoom_instance, task, **kwargs):
        super().__init__()
        self.kiwoom = kiwoom_instance
        self.task = task
        self.kwargs = kwargs


    def run(self):
        if self.task == "login":
            self.kiwoom.login()
        elif self.task == "monitor":
            codes_str = self.kwargs.get("codes_str")
            self.kiwoom.subscribe_realtime_data("0101", codes_str)
            self.exec_()
                 

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.kiwoom = KiwoomAPI()
        self.worker = None
        self.ai_process = None

        self.signal_server = SignalServerThread()
        self.signal_server.order_signal.connect(self.on_ai_signal_received)
        self.initUI()

        self.kiwoom.log_signal.connect(self.update_log)
        self.kiwoom.login_success_signal.connect(self.on_login_success)
        self.kiwoom.candle_completed_signal.connect(self.on_candle_completed)
        self.kiwoom.order_result_signal.connect(self.on_order_result)

    def initUI(self):
        self.setWindowTitle('AI 자동매매 시스템 v3.0 - 최종 관제탑')
        self.setGeometry(300, 300, 600, 500) #x, y, 너비, 높이

        try:
            with open("C:/program trading system/watchlist.txt") as f:
                first_stock = f.readline().strip()
            if not first_stock:
                first_stock = "005930"
        except FileNotFoundError:
            first_stock = "005930"

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_vbox = QVBoxLayout()
        central_widget.setLayout(main_vbox)

        top_hbox = QHBoxLayout()
        self.account_label = QLabel('계좌번호: 미연결')
        self.stock_code_label = QLabel('종목코드:')
        self.stock_code_input = QLineEdit(first_stock)
        top_hbox.addWidget(self.account_label)
        top_hbox.addWidget(self.stock_code_label)
        top_hbox.addWidget(self.stock_code_input)

        button_hbox = QHBoxLayout()
        self.start_button = QPushButton('1. 키움증권 로그인')
        self.monitor_button = QPushButton('2. 실시간 모니터링 시작')
        self.ai_button = QPushButton('3. AI 컨트롤러 시작')
        self.exit_button = QPushButton('프로그램 종료')
        self.exit_button.clicked.connect(self.close)

        self.monitor_button.setDisabled(True)
        self.ai_button.setDisabled(True)
        
        button_hbox.addWidget(self.start_button)
        button_hbox.addWidget(self.monitor_button)
        button_hbox.addWidget(self.ai_button)
        button_hbox.addWidget(self.exit_button)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)

        main_vbox.addLayout(top_hbox)
        main_vbox.addLayout(button_hbox)
        main_vbox.addWidget(self.log_box)

        self.statusBar = self.statusBar()
        self.statusBar.showMessage("준비 중...")

        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.update_time)


        self.start_button.clicked.connect(self.start_login)
        self.monitor_button.clicked.connect(self.start_monitoring)
        self.ai_button.clicked.connect(self.start_ai_controller)

        self.show()
    
    def start_login(self):
        self.worker = KiwoomWorker(self.kiwoom, "login")
        self.worker.start()
        self.start_button.setDisabled(True)

    def start_monitoring(self):
        try:
            with open("C:/program trading system/watchlist.txt", "r") as f: codes = [line.strip() for line in f.readlines() if line.strip()]
            if not codes: self.update_log("오류: watchlist.txt가 비어있습니다."); return
            worker = KiwoomWorker(self.kiwoom, "monitor", codes_str=";".join(codes)); worker.start(); self.worker = worker
            self.monitor_button.setDisabled(True); self.monitor_button.setText("모니터링 중...")
        except Exception as e: self.update_log(f"모니터링 시작 오류: {e}")

    def start_ai_controller(self):
        self.update_log("AI 엔진 연구소를 가동합니다...")
        try:
            py_64bit_path = "C:/Users/pc/AppData/Local/Programs/Python/Python313/python.exe"
            ai_controller_script_path = "C:/program trading system/ai_research_64bit/ai_controller.py"

            self.ai_process = subprocess.Popen([py_64bit_path, ai_controller_script_path])
            self.update_log("AI 컨트롤러가 백그라운드에서 실행되었습니다.")
            self.ai_button.setText("AI 가동 중...")
            self.ai_button.setDisabled(True)
        except Exception as e:
            self.update_log(f"AI 컨트롤라 실행 실패: {e}")
            
    def update_time(self):
        """
        [수정] 매초마다 현재 시간과 함께, 다음 3분봉까지 남은 시간을 계산하여 상태바에 표시합니다.
        """
        now = QDateTime.currentDateTime()
        
        # 다음 3분봉 시간 계산
        current_minute = now.time().minute()
        minutes_to_next_window = 3 - (current_minute % 3)
        seconds_to_next_window = 60 - now.time().second()
        
        # 실제 남은 시간 계산 (분, 초)
        remaining_minutes = minutes_to_next_window - 1
        remaining_seconds = seconds_to_next_window
        
        if seconds_to_next_window == 60:
            remaining_minutes += 1
            remaining_seconds = 0
            
        # 상태 메시지 설정
        status_message = f"현재시간: {now.toString('yyyy-MM-dd hh:mm:ss')}"
        if self.monitor_button.isEnabled() == False: # 모니터링이 시작되었을 때만 진행도 표시
            status_message += f" | 다음 캔들까지: {remaining_minutes}분 {remaining_seconds}초"
            
        self.statusBar.showMessage(status_message)
    
    def update_log(self, message):
        self.log_box.append(str(message))

    def on_login_success(self):
        self.update_log("로그인 성공!")
        self.start_button.setDisabled(True)
        self.start_button.setText("로그인 완료")
        self.monitor_button.setDisabled(False)
        self.ai_button.setDisabled(False)
        self.update_data_button.setDisabled(False)

        self.account_label.setText(f"계좌번호: {self.kiwoom.account_number}")
        self.statusBar.showMessage(f"현재시간: {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')} | 상태: 로그인 완료")

        self.update_log("주문 신호 감지를 시작합니다...")
        self.signal_server.start()


    def on_ai_signal_received(self, message):
        try:
            parts = message.split(',')
            if len(parts) == 3:
                signal, code, qty_str = parts
                qty = int(qty_str)
                self.update_log(f"!!! [직통 신호] {code} 종목, {qty}주 {signal} 주문 실행!!!")
                order_type = 1 if signal == "BUY" else 2
                order_kwargs = {
                    "rqname": f"AIBot_{signal}_{code}", "screen_no": "0101",
                    "acc_no": self.kiwoom.account_number, "order_type": order_type,
                    "code": code, "qty": qty, "price": 0, "hoga_gb": "03" # 시장가 주문
                }
                worker = KiwoomWorker(self.kiwoom, "order", **order_kwargs)
                worker.start()
        except Exception as e:
            self.update_log(f"신호 처리 중 오류: {e}")
        

    
    def on_candle_completed(self, candle_data):
        code = candle_data.get('code')
        if not code: return
        try:
            live_data_dir = "C:/program trading system/data/live_data"
            if not os.path.exists(live_data_dir): os.makedirs(live_data_dir)
            live_data_path = os.path.join(live_data_dir, f"live_{code}.csv")
            df = pd.DataFrame([candle_data])
            if not os.path.exists(live_data_path):
                df.to_csv(live_data_path, index=False, encoding='utf-8-sig')
            else:
                df.to_csv(live_data_path, mode='a', header=False, index=False, encoding='utf-8-sig')
        except Exception as e: self.update_log(f"[{code}] 캔들 저장 오류: {e}")

        
    def closeEvent(self, event):
        if self.ai_process:
            self.ai_process.terminate()
        self.signal_server.stop()
        self.signal_server.wait()
        QApplication.instance().quit()
        event.accept()
    
    def log_trade(self, trade_data):
        log_path = "C:/program trading system/trade_log.csv"
        file_exists = os.path.isfile(log_path)

        with open(log_path, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['체결시간', '주문유형', '종목코드', '체결가격', '체결수량', '손익'])
            
            writer.writerow([
                trade_data.get('체결시간'),
                trade_data.get('주문유형'),
                trade_data.get('종목코드'),
                trade_data.get('체결가격'),
                trade_data.get('체결수량'),
                trade_data.get('손익', 0)
            ])
    
    def on_order_result(self, result_data):
        self.update_log(f"[주문 결과] {result_data}")
        if result_data.get("주문상태") == "체결":
            self.log_trade(result_data)
            self.update_log(f"*** [거래기록] {result_data.get('종목코드')} 체결 내역을 trade_log.csv에 저장했습니다. ***")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())