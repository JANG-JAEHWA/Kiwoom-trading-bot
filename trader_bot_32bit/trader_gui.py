import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QPushButton, QTextEdit, QLabel, QLineEdit, QHBoxLayout)
from PyQt5.QtCore import  QThread, pyqtSignal, QTimer, QDateTime
from kiwoom_api import KiwoomAPI
import pandas as pd


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
            code = self.kwargs.get("code")
            self.kiwoom.subscribe_realtime_data("0101", code, "20;10;15", "0")
                 

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.kiwoom = KiwoomAPI()
        self.worker = None
        self.ai_process = None
        self.initUI()

        self.kiwoom.log_signal.connect(self.update_log)
        self.kiwoom.login_success_signal.connect(self.on_login_success)
        self.kiwoom.candle_completed_signal.connect(self.on_candle_completed)

    def initUI(self):
        self.setWindowTitle('AI 자동매매 시스템 v2.0 - 통합 관제')
        self.setGeometry(300, 300, 600, 500) #x, y, 너비, 높이

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_vbox = QVBoxLayout()
        central_widget.setLayout(main_vbox)

        top_hbox = QHBoxLayout()
        self.account_label = QLabel('계좌번호: 미연결')
        self.stock_code_label = QLabel('종목코드:')
        self.stock_code_input = QLineEdit('005930')
        top_hbox.addWidget(self.account_label)
        top_hbox.addWidget(self.stock_code_label)
        top_hbox.addWidget(self.stock_code_input)

        button_hbox = QHBoxLayout()
        self.start_button = QPushButton('1. 키움증권 로그인')
        self.monitor_button = QPushButton('2. 실시간 모니터링 시작')
        self.ai_button = QPushButton('3. AI 컨트롤러 시작')
        self.update_data_button = QPushButton('데이터 최신화')
        self.exit_button = QPushButton('프로그램 종료')
        self.exit_button.clicked.connect(self.close)

        self.monitor_button.setDisabled(True)
        self.ai_button.setDisabled(True)
        self.update_data_button.setDisabled(True)
        
        button_hbox.addWidget(self.start_button)
        button_hbox.addWidget(self.monitor_button)
        button_hbox.addWidget(self.update_data_button)
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
        self.update_data_button.clicked.connect(self.start_data_update)
        self.ai_button.clicked.connect(self.start_ai_controller)

        self.show()
    
    def start_login(self):
        self.worker = KiwoomWorker(self.kiwoom, "login")
        self.worker.start()
        self.start_button.setDisabled(True)

    def start_monitoring(self):
        code = self.stock_code_input.text()
        self.update_log(f"{code} 종목 실시간 모니터링을 시작합니다.")
        self.worker = KiwoomWorker(self.kiwoom, "monitor", code=code)
        self.worker.start()
        self.start_button.setText("모니터링 중...")
        self.start_button.setDisabled(True)

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

    def start_data_update(self):
        self.update_log("'데이터 최신화'를 시작합니다. 새 터미널 창에서 확인하세요...")
        try:
            py_32bit_path = "C:/Users/pc/AppData/Local/Programs/Python/Python39-32/python.exe"
            collector_script_path = "C:/program trading system/trader_bot_32bit/collector.py"

            subprocess.Popen([py_32bit_path, collector_script_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            self.update_log("데이터 수집기가 백그라운드에서 실행되었습니다.")
        except Exception as e:
            self.update_log(f"데이터 수집기 실행 실패: {e}")
            
    def update_time(self):
        currentTime = QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')
        self.statusBar.showMessage(f"현재시간: {currentTime} | 상태: 준비 중")
    
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
    
    def on_candle_completed(self, candle_data):
        self.update_log(f"[3분봉 완성] {candle_data}")
        try:
            live_data_path = "../data/live_data.csv"
            df = pd.DataFrame([candle_data])

            if not os.path.exists(live_data_path):
                df.to_csv(live_data_path, index=False, encoding='utf-8-sig')
            else:
                df.to_csv(live_data_path, mode='a', header=False, index=False, encoding='utf-8-sig')
        except Exception as e:
            self.update_log(f"파일 저장 중 오류 발생: {e}")

        
    def closeEvent(self, event):
        if self.ai_process:
            self.ai_process.terminate()
        QApplication.instance().quit()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())