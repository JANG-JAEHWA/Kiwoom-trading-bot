import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QPushButton, QTextEdit, QLabel, QLineEdit, QHBoxLayout)
from PyQt5.QtCore import  QThread, pyqtSignal, QTimer, QDateTime
from kiwoom_api import KiwoomAPI

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
    
    def set_task(self, task, **kwargs):
        self.task = task
        self.kwargs = kwargs                     

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.kiwoom = KiwoomAPI()
        self.worker = None

        self.initUI()

        self.kiwoom.log_signal.connect(self.update_log)
        self.kiwoom.login_success_signal.connect(self.on_login_success)
        self.kiwoom.candle_completed_signal.connect(self.on_candle_completed)

    def initUI(self):
        self.setWindowTitle('AI 자동매매 시스템 v1.2')
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
        self.exit_button = QPushButton('프로그램 종료')
        self.exit_button.clicked.connect(self.close)
        
        button_hbox.addWidget(self.start_button)
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

        self.stock_code_label = QLabel('모니터링할 종목 코드:')

        self.start_button.clicked.connect(self.on_start_button_clicked)
        self.show()
    
    def update_time(self):
        currentTime = QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')
        self.statusBar.showMessage(f"현재시간: {currentTime} | 상태: 준비 중")
    
    def on_start_button_clicked(self):
        if self.kiwoom.get_connect_state() == 0:
            self.worker = KiwoomWorker(self.kiwoom, "login")
            self.worker.start()
            self.start_button.setDisabled(True)
        else:
            code = self.stock_code_input.text()
            self.update_log(f"{code} 종목 실시간 모니터링을 시작합니다.")
            self.worker = KiwoomWorker(self.kiwoom, "monitor", code=code)
            self.worker.start()
            self.start_button.setText("모니터링 중...")
            self.start_button.setDisabled(True)
    
    def update_log(self, message):
        self.log_box.append(str(message))

    def on_login_success(self):
        self.update_log("로그인 성공! 다음 단계를 진행할 수 있습니다.")
        self.start_button.setText("2. 실시간 모니터링 시작")
        self.start_button.setDisabled(False)

        self.account_label.setText(f"계좌번호: {self.kiwoom.account_number}")
        self.statusBar.showMessage(f"현재시간: {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')} | 상태: 로그인 완료")
    
    def on_candle_completed(self, candle_data):
        self.update_log(f"[3분봉 완성] {candle_data}")
        
    def closeEvent(self, event):
        QApplication.instance().quit()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())