from PyQt5.QtCore import QEventLoop, QDateTime, QObject, pyqtSignal, QTimer
from PyQt5.QAxContainer import QAxWidget
import datetime
class KiwoomAPI(QObject):
    log_signal = pyqtSignal(str)
    login_success_signal = pyqtSignal()
    candle_completed_signal = pyqtSignal(dict)
    order_result_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(str)

    collection_done_signal = pyqtSignal()
    page_data_received_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.api = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self._set_event_handlers()

        self.login_event_loop = QEventLoop()
        self.tr_event_loop = None

        self.account_number = None
        self.tr_data = None
        self.prev_next = "0"
        self.current_code = ""
        self.req_manager = None

        self.current_candles = {}
        self.current_window_start_time = None

    def _set_event_handlers(self):
        """이벤트와 이벤트 핸들러를 연결합니다."""
        self.api.OnEventConnect.connect(self._event_connect)
        self.api.OnReceiveTrData.connect(self._receive_tr_data)
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
        self.log_signal.emit(f"[{code_list_str}] 실시간 데이터 구독을 신청합니다.")
        self.api.SetRealReg(screen_no, code_list_str, "20;10;15", "0")

    def disconnect_realtime_data(self, screen_no="0101"):
        self.api.DisconnectRealData(screen_no)
    
    def _receive_real_data(self, code, real_type, real_data):
        if real_type == "주식체결":
            try:
                trade_time_str = self.api.GetCommRealData(code, 20)
                current_price = abs(int(self.api.GetCommRealData(code, 10)))
                trade_volume = abs(int(self.api.GetCommRealData(code, 15)))

                now = QDateTime.currentDateTime()
                trade_time = QDateTime.fromString(now.toString('yyyyMMdd') + trade_time_str, 'yyyyMMddHHmmss')
                minute = trade_time.time().minute()
                window_minute = (minute // 3) * 3
                window_start_qtime = QDateTime(trade_time.date(), trade_time.time().toPyTime().replace(minute=window_minute, second=0, microsecond=0))
                
                if code not in self.current_candles:
                    self.current_candles[code] = {'start_time': None, 'data': {}}

                current_candle_info = self.current_candles[code]
                if current_candle_info['start_time'] is None or window_start_qtime > current_candle_info['start_time']:
                    if current_candle_info['data']:
                        self.candle_completed_signal.emit(current_candle_info['data'])
                    current_candle_info['start_time'] = window_start_qtime
                    current_candle_info['data'] = {
                        'code': code,
                        'date': window_start_qtime.toString('yyyyMMddHHmmss'),
                        'open': current_price,
                        'high': current_price,
                        'low': current_price,
                        'close': current_price,
                        'volume': trade_volume
                    }
                else:
                    candle = current_candle_info['data']
                    candle['high'] = max(candle['high'], current_price)
                    candle['low'] = min(candle['low'], current_price)
                    candle['close'] = current_price
                    candle['volume'] += trade_volume
            except Exception as e:
                print(f"!!! CRITICAL ERROR in _receive_real_data: {e}")
                self.log_signal.emit(f"실시간 데이터 처리 오류: {e}")

    def send_order(self, rqname, screen_no, acc_no, order_type, code, qty, price, hoga_gb, org_order_no):
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
        self.log_signal.emit(f"\n[{code}] {qty}주 주문 전송을 시도합니다...")
        self.api.SendOrder(
            rqname, screen_no, acc_no, order_type, code, qty, price, hoga_gb, org_order_no
        )
        self.order_event_loop.exec_()

    def _receive_chejan_data(self, gubun, item_cnt, fid_list):
        """
        gubun 0: 주문 접수/채결, 1: 국내주식 잔고
        """
        if gubun == "0":
            order_status = self.api.GetChejanData(913).strip() # 주문상태
            stock_code = self.api.GetChejanData(9001)[1:].strip() # 종목코드
            order_no = self.api.GetChejanData(9203).strip() # 주문번호
            order_type_raw = self.api.GetChejanData(907).strip() # 매도수구분 (+매도, -매수)

            executed_price_str = self.api.GetChejanData(910).strip()# 체결가
            executed_qty_str = self.api.GetChejanData(911).strip() # 체결수량

            executed_price = int(executed_price_str) if executed_price_str else 0
            executed_qty = int(executed_qty_str) if executed_qty_str else 0

            order_type = "매도" if order_type_raw == "+매도" else "매수"

            if order_status == "채결":
                result = {
                    "체결시간": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                    "주문유형": order_type, 
                    "종목코드": stock_code,
                    "주문번호": order_no, 
                    "체결가격": executed_price, 
                    "체결수량": executed_qty
                }
                self.order_result_signal.emit(result)
            if order_status in ["접수", "체결"]:
                if hasattr(self, 'order_event_loop') and self.order_event_loop.isRunning():
                    self.order_event_loop.exit()

    def get_code_list(self, market_code):
        return self.api.GetCodeListByMarket(market_code).split(';')[:-1]

    def get_connect_state(self):
        return self.api.GetConnectState() #0-미연결, 1-연결
    
    def get_minute_data_page(self, code, tick_range=3, is_continuous_request=False):
        tr_event_loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(tr_event_loop.quit)

        self.tr_event_loop = tr_event_loop

        self.tr_data = None 
        self.api.SetInputValue("종목코드", code)
        self.api.SetInputValue("틱범위", str(tick_range))
        self.api.SetInputValue("수정주가구분", "1")
        
        timer.start(10000) 
        self.api.CommRqData("주식분봉차트조회", "opt10080", 2 if is_continuous_request else 0, "0101")
        tr_event_loop.exec_()

        is_timed_out = not timer.isActive()
        timer.stop()
        
        if is_timed_out:
            print(f"\n-> [경고] {code} 종목 요청 시간 초과.")
            return None, "0"
            
        return self.tr_data, self.prev_next

    def _receive_tr_data(self, screen_no, rqname, trcode, record_name, prev_next, *args):
        self.prev_next = prev_next
        if rqname == "주식분봉차트조회":
            count = self.api.GetRepeatCnt(trcode, rqname)
            data_list =[]
            for i in range(count):
                try:
                    item = {
                        'date': self.api.GetCommData(trcode, rqname, i, "체결시간" if rqname == "주식분봉차트조회" else "일자").strip(),
                        'open': abs(int(self.api.GetCommData(trcode, rqname, i, "시가"))),
                        'high': abs(int(self.api.GetCommData(trcode, rqname, i, "고가"))),
                        'low': abs(int(self.api.GetCommData(trcode, rqname, i, "저가"))),
                        'close': abs(int(self.api.GetCommData(trcode, rqname, i, "현재가"))),
                        'volume': int(self.api.GetCommData(trcode, rqname, i, "거래량"))
                    }
                    data_list.append(item)
                except (ValueError, TypeError):
                    continue
            self.tr_data = data_list
        if hasattr(self, 'tr_event_loop') and self.tr_event_loop.isRunning():
            self.tr_event_loop.exit()

    
    def start_collecting_minute_data(self, code, tick_range=3, is_continuous_request=False):
        self.current_code = code
        
        self.api.SetInputValue("종목코드", code)
        self.api.SetInputValue("틱범위", str(tick_range))
        self.api.SetInputValue("수정주가구분", "1")
        self.api.CommRqData("주식분봉차트조회", "opt10080", 2 if is_continuous_request else 0, "0101")

    def set_request_manager(self, req_manager):
        self.req_manager = req_manager
    
    def get_stock_state(self, code):
        return self.api.GetMasterStockState(code)