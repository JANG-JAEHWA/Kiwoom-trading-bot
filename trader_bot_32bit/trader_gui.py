import sys, os, subprocess, socket, csv, pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QHBoxLayout
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QDateTime
from kiwoom_api_trader import KiwoomAPI

class SignalServerThread(QThread):
    order_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_running = True
    
    def run(self):   
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 9999)); s.listen()
            print("[Signal Server] AI 컨트롤러의 접속을 기다립니다...")
            conn, addr = s.accept()
            with conn:
                print(f"[Signal Server] AI 컨트롤러 접속: {addr}")
                while self.is_running:
                    try:
                        data = conn.recv(1024)
                        if not data: break
                        message = data.decode()
                        self.order_signal.emit(message)
                    except ConnectionAbortedError: break # 클라이언트가 연결을 끊으면 루프 종료
        print("[Signal Server] 연결이 종료되었습니다.")
        
    def stop(self):
        self.is_running = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', 9999))
        except ConnectionRefusedError:
            pass


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
            self.exec_() # 실시간 이벤트를 계속 받기 위해 이벤트 루프 실행
        elif self.task == "order":
            self.kiwoom.send_order(**self.kwargs)
                 

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.kiwoom = KiwoomAPI()
        self.worker = None
        self.ai_process = None
        self.order_workers = []

        self.signal_server = SignalServerThread()
        self.signal_server.order_signal.connect(self.on_ai_signal_received)
        self.initUI()

        self.kiwoom.log_signal.connect(self.update_log)
        self.kiwoom.login_success_signal.connect(self.on_login_success)
        self.kiwoom.candle_1min_completed_signal.connect(self.on_1min_candle_completed)
        self.kiwoom.candle_3min_completed_signal.connect(self.on_3min_candle_completed)
        self.kiwoom.order_result_signal.connect(self.on_order_result)

    def initUI(self):
        self.setWindowTitle('AI Trader v4.0'); self.setGeometry(300, 300, 600, 400)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        btn_layout = QHBoxLayout()
        self.start_button, self.monitor_button, self.ai_button, self.exit_button = QPushButton('1. 로그인'), QPushButton('2. 모니터링 시작'), QPushButton('3. AI 컨트롤러 시작'), QPushButton('종료')
        self.monitor_button.setDisabled(True)
        self.ai_button.setDisabled(True)
        for btn in [self.start_button, self.monitor_button, self.ai_button, self.exit_button]: btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)
        layout.addWidget(self.log_box)
        self.start_button.clicked.connect(self.start_login)
        self.monitor_button.clicked.connect(self.start_monitoring)
        self.ai_button.clicked.connect(self.start_ai_controller)
        self.exit_button.clicked.connect(self.close)
        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.update_time)
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
        now = QDateTime.currentDateTime()
        status = f"현재시간: {now.toString('yyyy-MM-dd hh:mm:ss')}"
        if not self.monitor_button.isEnabled():
            s = now.time().second()
            m = now.time().minute()
            status += f" | 1분봉: {59-s}초 후 | 3분봉: {2-(m%3)}분 {59-s}초 후"
        self.statusBar().showMessage(status)
    
    def update_log(self, message):
        self.log_box.append(str(message))

    def on_login_success(self):
        self.update_log("로그인 성공!")
        self.start_button.setDisabled(True)
        self.start_button.setText("로그인 완료")
        self.monitor_button.setDisabled(False)
        self.ai_button.setDisabled(False)

        self.update_log(f"로그인 성공. 계좌번호: {self.kiwoom.account_number}")
        self.statusBar().showMessage(f"현재시간: {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')} | 상태: 로그인 완료")

        self.update_log("주문 신호 감지를 시작합니다...")
        self.signal_server.start()


    def on_ai_signal_received(self, message):
        self.update_log(f"!!! [직통 신호] {message} 수신 !!!")
        try:
            signal, code, qty_str = message.split(','); qty = int(qty_str)
            if "BUY" in signal:
                order_type = 1 # 신규매수
            elif "SELL" in signal:
                order_type = 2 # 신규매도
            else:
                self.update_log(f"알 수 없는 신호 타입: {signal}")
                return
            order_kwargs = {"rqname": f"AI_{signal}_{code}", "screen_no": "0101", "acc_no": self.kiwoom.account_number, "order_type": order_type, "code": code, "qty": qty, "price": 0, "hoga_gb": "03"}
            order_worker = KiwoomWorker(self.kiwoom, "order", **order_kwargs)
            order_worker.start(); self.order_workers.append(order_worker)
        except Exception as e: self.update_log(f"신호 처리 오류: {e}")
        
    def on_1min_candle_completed(self, candle_data):
        self.save_candle_data(candle_data, "1min")

    def on_3min_candle_completed(self, candle_data):
        self.save_candle_data(candle_data, "3min")
    
    def save_candle_data(self, candle_data, interval_str):
        try:
            code = candle_data.get('code')
            if not code: return

            live_data_dir = f"C:/program trading system/data/live_data_{interval_str}"
            if not os.path.exists(live_data_dir): os.makedirs(live_data_dir)

            live_data_path = os.path.join(live_data_dir, f"live_{code}.csv")

            df = pd.DataFrame([candle_data])
            header = not os.path.exists(live_data_path)
            
            df.to_csv(live_data_path, mode='a', header=header, index=False, encoding='utf-8-sig')
            if interval_str == "3min":
                self.update_log(f"[{code}] 3분봉 데이터 저장 완료")
            
        except Exception as e: self.update_log(f"[{code}] {interval_str} 캔들 저장 오류: {e}")

        
    def closeEvent(self, event):
        if self.ai_process:
            self.ai_process.terminate()
        self.signal_server.stop()
        self.signal_server.wait()
        QApplication.instance().quit()
        event.accept()
    
    def log_trade(self, data):
        path = "C:/program trading system/trade_log.csv"
        header = not os.path.exists(path)
        data['체결시간'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(path, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['체결시간', '주문유형', '종목코드', '체결가격', '체결수량'])
            if header: writer.writeheader()
            writer.writerow({k: data.get(k, '') for k in writer.fieldnames})
        
    
    def on_order_result(self, data):
        self.update_log(f"[주문 결과] {data}")
        if data.get("주문상태") == "체결":
            self.log_trade(data)
            self.update_log(f"*** [거래 기록] {data.get('종목코드')} 체결 내역 저장 완료 ***")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())