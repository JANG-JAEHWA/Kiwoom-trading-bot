from PyQt5.QtCore import QEventLoop, QDateTime, QObject, pyqtSignal
from PyQt5.QAxContainer import QAxWidget
import datetime

class KiwoomAPI(QObject):
    log_signal = pyqtSignal(str)
    login_success_signal = pyqtSignal()
    candle_1min_completed_signal = pyqtSignal(dict)
    candle_3min_completed_signal = pyqtSignal(dict)
    order_result_signal = pyqtSignal(dict)

    orderbook_update_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.api = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self._set_event_handlers()

        self.login_event_loop = QEventLoop()
        self.order_event_loop = None
        self.account_number = None

        self.candles_1min = {}
        self.candles_3min = {}

    def _set_event_handlers(self):
        """이벤트와 이벤트 핸들러를 연결합니다."""
        self.api.OnEventConnect.connect(self._event_connect)
        self.api.OnReceiveRealData.connect(self._receive_real_data)
        self.api.OnReceiveChejanData.connect(self._receive_chejan_data)
    
    def login(self):
        """
        로그인 창을 띄우고, 응답이 올 때까지 대기합니다.
        """
        self.log_signal.emit("로그인을 시도합니다.")
        self.api.CommConnect()
        self.login_event_loop.exec_()

    def _event_connect(self, err_code):
        """
        로그인 성공/실패 시 이벤트 핸들러
        err_code가 0이면 성공입니다.
        """
        if err_code == 0:
            self.account_number = self.api.GetLoginInfo("ACCNO").split(';')[0]
            self.log_signal.emit("로그인에 성공했습니다.")
            self.log_signal.emit(f"계좌번호: {self.account_number}")
            self.login_success_signal.emit()
        else:
            self.log_signal.emit(f"로그인에 실패했습니다. 에러 코드: {err_code}")
        self.login_event_loop.exit()

    def subscribe_realtime_data(self, screen_no, code_list_str):
        fids = "20;10;15;227;228;41;42;43;44;45;46;47;48;49;50;51;52;53;54;55;56;57;58;59;60;61;71;125;129"
        self.log_signal.emit(f"[{code_list_str}] 실시간 데이터 구독을 신청합니다.")
        self.api.SetRealReg(screen_no, code_list_str,fids, "1")

    def _receive_real_data(self, code, real_type, real_data):
        if real_type == "주식체결":
            try:
                price_str = self.api.GetCommRealData(code, 10)
                volume_str = self.api.GetCommRealData(code, 15)
                time_str = self.api.GetCommRealData(code, 20)
                vi_static_str = self.api.GetCommRealData(code, 227)
                vi_dynamic_str = self.api.GetCommRealData(code, 228)

    
                if not all([price_str, volume_str, time_str]):
                    return

                price = abs(int(float(price_str)))
                volume = abs(int(float(volume_str)))
                vi_static_price = abs(int(float(vi_static_str))) if vi_static_str else 0
                vi_dynamic_price = abs(int(float(vi_dynamic_str))) if vi_dynamic_str else 0

                now = QDateTime.currentDateTime()
                trade_time = QDateTime.fromString(now.toString('yyyyMMdd') + time_str, 'yyyyMMddHHmmss')
                self._update_candle(code, price, volume, trade_time, 1, vi_static_price, vi_dynamic_price)
                self._update_candle(code, price, volume, trade_time, 3, vi_static_price, vi_dynamic_price)
            except Exception as e:
                self.log_signal.emit(f"[{code}] 실시간 데이터 처리 오류: {e}")
        elif real_type == "주식호가잔량":
            try:
                orderbook = {'code': code}
                for i in range(10):
                    orderbook[f'sell_price_{i+1}'] = abs(int(float(self.api.GetCommRealData(code, 41 + i))))
                    orderbook[f'sell_qty_{i+1}'] = abs(int(float(self.api.GetCommRealData(code, 61 + i))))

                    orderbook[f'buy_price_{i+1}'] = abs(int(float(self.api.GetCommRealData(code, 51 + i))))
                    orderbook[f'buy_qty_{i+1}'] = abs(int(float(self.api.GetCommRealData(code, 71 + i))))

                orderbook[f'total_sell_qty'] = abs(int(float(self.api.GetCommRealData(code, 125))))
                orderbook[f'total_buy_qty'] = abs(int(float(self.api.GetCommRealData(code, 129))))

                self.orderbook_update_signal.emit(orderbook)
            except Exception as e:
                self.log_signal.emit(f"[{code}] 호가 데이터 처리 오류: {e}")

    def _update_candle(self, code, price, volume, trade_time, interval, vi_static, vi_dynamic):
            candles = self.candles_1min if interval == 1 else self.candles_3min
            signal_emitter = self.candle_1min_completed_signal if interval == 1 else self.candle_3min_completed_signal
            
            minute = trade_time.time().minute()
            window_minute = (minute // interval) * interval
            start_time = QDateTime(trade_time.date(), trade_time.time().toPyTime().replace(minute=window_minute, second=0, microsecond=0))
                
            if code not in candles:
                candles[code] = {'start_time': None, 'data': {}}

            candle_info = candles[code]
            if candle_info['start_time'] is None or start_time > candle_info['start_time']:
                if candle_info['data']:
                    signal_emitter.emit(candle_info['data'])
                candle_info['start_time'] = start_time
                candle_info['data'] = {
                    'code': code,
                    'date': start_time.toString('yyyyMMddHHmmss'),
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume,
                    'vi_static_price': vi_static,
                    'vi_dynamic_price': vi_dynamic
                }
            else:
                candle = candle_info['data']
                candle['high'] = max(candle['high'], price)
                candle['low'] = min(candle['low'], price)
                candle['close'] = price
                candle['volume'] += volume
                candle['vi_static_price'] = vi_static
                candle['vi_dynamic_price'] = vi_dynamic
            

    def send_order(self, rqname, screen_no, acc_no, order_type, code, qty, price, hoga_gb, org_order_no=""):
        """
        주식 주문을 서버로 전송하는 함수
        
        rqname: 사용자가 구분할 요청 이름
        screen_no: 화면번호 (보통 4자리 숫자, 0101 등)
        acc_no: 계좌번호 10자리
        order_type: 주문유형 (1:신규매수, 2:신규매도, 3:매수취소, 4:매도취소...)
        code: 종목코드 (예: "005930")
        qty: 주문수량
        price: 주문가격 (시장가 주문 시 0)
        hoga_gb: 거래구분(가격 유형) ("00":지정가, "03":시장가)
        org_order_no: 원주문번호 (정정/취소 주문 시 사용, 신규 주문은 "")
        """
        self.log_signal.emit(f"\n[{code}] {qty}주 {'매수' if order_type == 1 else '매도'} 주문 전송을 시도합니다...")
        self.order_event_loop = QEventLoop()
        self.api.SendOrder(
            rqname, screen_no, acc_no, order_type, code, qty, price, hoga_gb, org_order_no
        )
        self.order_event_loop.exec_()

    def _receive_chejan_data(self, gubun, item_cnt, fid_list):
        """
        gubun 0: 주문 접수/채결, 1: 국내주식 잔고
        """
        if gubun == "0":
            order_status = self.api.GetChejanData(913).strip()

            if order_status in ["접수", "체결"]:
                if hasattr(self, 'order_event_loop') and self.order_event_loop.isRunning():
                    self.order_event_loop.exit()
            
            if order_status == "체결":
                stock_code = self.api.GetChejanData(9001)[1:].strip()
                order_no = self.api.GetChejanData(9203).strip()
                order_gubun = self.api.GetChejanData(905).strip()
                order_type = "매도" if "매도" in order_gubun else "매수"
                executed_time_str = self.api.GetChejanData(908).strip()
                executed_price = int(self.api.GetChejanData(910).strip())
                executed_qty = int(self.api.GetChejanData(911).strip())
                self.order_result_signal.emit({"주문상태": order_status,
                                                "주문유형": order_type, 
                                                "종목코드": stock_code,
                                                "주문번호": order_no, 
                                                "체결시간": executed_time_str,
                                                "체결가격": executed_price, 
                                                "체결수량": executed_qty
                })
            if hasattr(self, 'order_event_loop') and self.order_event_loop.isRunning():
                self.order_event_loop.exit()

    def get_connect_state(self):
        return self.api.GetConnectState() #0-미연결, 1-연결