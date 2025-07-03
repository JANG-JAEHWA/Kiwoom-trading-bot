import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QPushButton, QTextEdit, QLabel, QLineEdit)
from PyQt5.QtCore import QCoreApplication, QThread, pyqtSignal
from kiwoom_api import KiwoomAPI

class KiwoomWorker(QThread):
    log_message = pyqtSignal(str)
    login_success = pyqtSignal()

    def __init__(self, kiwoom_instance):
        super().__init__()
        self.kiwoom = kiwoom_instance

    def run(self):
        try:
            self.log_message.emit("키움 API worker 시작...")

            self.kiwoom.log_signal = self.log_message

            self.kiwoom.login()
            self.login_success.emit()
        except Exception as e:
            self.log_message.emit(f"워커 실행 중 오류 발생: {e}")


class MainWindow(QMainWindow):
    def __init__(self, kiwoom_instance):
        super().__init__()
        self.kiwoom = kiwoom_instance
        self.worker = KiwoomWorker(self.kiwoom)
        self.worker.log_message.connect(self.update_log)
        self.worker.login_success.connect(self.on_login_success)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('AI 자동매매 시스템 v0.2 - 로그인')
        self.setGeometry(300, 300, 500, 400) #x, y, 너비, 높이

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        vbox = QVBoxLayout()
        central_widget.setLayout(vbox)

        self.stock_code_label = QLabel('모니터링할 종목 코드:')
        self.stock_code_input = QLineEdit('005930')
        self.start_button = QPushButton('1. 키움증권 로그인')
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)

        vbox.addWidget(self.stock_code_label)
        vbox.addWidget(self.stock_code_input)
        vbox.addWidget(self.start_button)
        vbox.addWidget(self.log_box)

        self.exit_button = QPushButton('프로그램 종료')
        self.exit_button.clicked.connect(QCoreApplication.instance().quit)
        vbox.addWidget(self.exit_button)

        self.start_button.clicked.connect(self.start_login)

        self.show()
    
    def start_login(self):
        self.update_log("로그인을 시작합니다...")
        self.worker.start()
        self.start_button.setDisabled(True)
    
    def update_log(self, message):
        self.log_box.append(message)

    def on_login_success(self):
        self.update_log("로그인 성공! 다음 단계를 진행할 수 있습니다.")
        self.start_button.setText("2. 실시간 모니터링 시작")
        self.start_button.setDisabled(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    kiwoom_main_instance = KiwoomAPI()
    ex = MainWindow(kiwoom_main_instance)
    sys.exit(app.exec_())
        
