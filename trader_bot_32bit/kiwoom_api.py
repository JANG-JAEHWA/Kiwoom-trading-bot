import time
from PyQt5.QtCore import QEventLoop, QDateTime
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget

class KiwoomAPI:
    def __init__(self):
        self.api = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self._set_event_handlers()
        self.login_event_loop = QEventLoop()
        self.tr_event_loop = QEventLoop()
        self.order_event_loop = QEventLoop()

        self.tr_data = None
        self.account_number = None
        
        self.current_candle = {}
        self.current_window_start_time = None
        self.log_signal = None

    def _set_event_handlers(self):
        """이벤트와 이벤트 핸들러를 연결합니다."""
        self.api.OnEventConnect.connect(self._event_connect)
        self.api.OnReceiveTrData.connect(self._receive_tr_data)
        self.api.OnReceiveChejanData.connect(self._receive_chejan_data)
        self.api.OnReceiveRealData.connect(self._receive_real_data)

    def login(self):
        """
        로그인 창을 띄우고, 응답이 올 때까지 대기합니다.
        """
        print("로그인을 시도합니다.")
        self.api.CommConnect()
        self.login_event_loop.exec_()

    def _event_connect(self, err_code):
        """
        로그인 성공/실패 시 이벤트 핸들러
        err_code가 0이면 성공입니다.
        """
        if err_code == 0:
            if self.log_signal:
                self.log_signal.emit("로그인에 성공했습니다.")
            self.account_number = self.api.GetLoginInfo("ACCNO").split(';')[0]
            print(f"성공적으로 계좌번호를 가져왔습니다: {self.account_number}")
        else:
            print(f"로그인에 실패했습니다. 에러 코드: {err_code}")

        self.login_event_loop.exit()

    def get_daily_data(self, code, start_date="20250627", continuous=False):
        """
        지정한 종목의 일봉 데이터를 요청합니다.
        TR 코드: opt10081
        """
        print(f"[{code}] 일봉 데이터 요청 중...")

        all_data = []
        
        self.api.SetInputValue("종목코드", code)
        self.api.SetInputValue("기준일자", start_date)
        self.api.SetInputValue("수정주가구분", "1")#1: 수정주가, 0: 원주가

        self.api.CommRqData("일봉데이터요청", "opt10081", 0, "0101")
        self.tr_event_loop.exec_()

        if self.tr_data:
            all_data.extend(self.tr_data)

        if continuous:
            while self.api.dynamicCall("GetGlobalVariable(QString)", "prev_next") == "2":
                print("연속 조회 진행 중...")
                time.sleep(0.2)

                self.api.SetInputValue("종목코드", code)
                self.api.SetInputValue("기준일자", start_date)
                self.api.SetInputValue("수정주가구분", "1")

                self.api.CommRqData("일봉데이터요청", "opt10081", 2, "0101")
                self.tr_event_loop.exec_()

                if self.tr_data:
                    all_data.extend(self.tr_data)
                else:
                    break
                      
        print(f"총 {len(all_data)}일치 데이터 수신 완료.")
        return all_data

    def _receive_tr_data(self, screen_no, rqname, trcode, record_name, prev_next, *args):
        """
        TR 요청에 대한 응답 수신 이벤트 핸들러
        """
        if rqname == "일봉데이터요청":
            print("일봉 데이터 수신 완료.")
            count = self.api.GetRepeatCnt(trcode, rqname)
            data_list = []
            for i in range(count):
                data = {
                    'date': self.api.GetCommData(trcode, rqname, i, "일자").strip(),
                    'open': int(self.api.GetCommData(trcode, rqname, i, "시가").strip()),
                    'high': int(self.api.GetCommData(trcode, rqname, i, "고가").strip()),
                    'low': int(self.api.GetCommData(trcode, rqname, i, "저가").strip()),
                    'close': int(self.api.GetCommData(trcode, rqname, i, "현재가").strip()),
                    'volume': int(self.api.GetCommData(trcode, rqname, i, "거래량").strip())
                }
                data_list.append(data)
            self.tr_data = data_list
        elif rqname == "주식분봉차트조회":
            print("분봉 데이터 수신.")
            count = self.api.GetRepeatCnt(trcode, rqname)

            if count == 0:
                self.tr_data = []
            else:
                data_list = []
                for i in range(count):
                    item = {
                        'date': self.api.GetCommData(trcode, rqname, i, "체결시간").strip(),
                        'open': abs(int(self.api.GetCommData(trcode, rqname, i, "시가"))),
                        'high': abs(int(self.api.GetCommData(trcode, rqname, i, "고가"))),
                        'low': abs(int(self.api.GetCommData(trcode, rqname, i, "저가"))),
                        'close': abs(int(self.api.GetCommData(trcode, rqname, i, "현재가"))),
                        'volume': int(self.api.GetCommData(trcode, rqname, i, "거래량"))
                    }
                    data_list.append(item)
                self.tr_event_loop.exit()

    def subscribe_realtime_data(self, screen_no, code_list_str, fid_list_str, real_type):
        """
        real_type: 0 - 최초구독, 1 - 종목 추가/삭제
        """
        print("실시간 데이터 구독을 신청합니다...")
        self.api.SetRealReg(screen_no, code_list_str, fid_list_str, real_type)
    def ubsubscribe_realtime_data(self, screen_no, code):
        self.api.SetRealRemove(screen_no, code)
    
    def _receive_real_data(self, code, real_type, real_data):
        if real_type == "주식체결":
            trade_time_str = self.api.GetCommRealData(code, 20)
            current_price = abs(int(self.api.GetCommRealData(code, 10)))
            trade_volume = abs(int(self.api.GetCommRealData(code, 15)))
            
            now = QDateTime.currentDateTime()
            trade_time = QDateTime.fromString(now.toString('yyyyMMdd') + trade_time_str, 'yyyyMMddHHmmss')

            minute = trade_time.time().minute()
            window_minute = (minute // 3) * 3
            window_start_time = trade_time.date().toString('yyyy-MM-dd') + f"{trade_time.time().hour():02d}:{window_minute:02d}:00"

            if window_start_time != self.current_window_start_time:
                if self.current_candle:
                    if hasattr(str, 'on_candle_completed'):
                        self.on_candle_completed(self.current_candle)
                self.current_window_start_time = window_start_time
                self.current_candle = {
                    'time': window_start_time,
                    'open': current_price,
                    'high': current_price,
                    'low': current_price,
                    'close': current_price,
                    'volume': trade_volume
                }
            else:
                self.current_candle['high'] = max(self.current_candle['high'],current_price)
                self.current_candle['low'] = min(self.current_candle['low'],current_price)
                self.current_candle['close'] = current_price
                self.current_candle['volume'] += trade_volume
                print(f"\r[실시간 업데이트] 현재가:{current_price:,} | 고가:{self.current_candle['high']:,} | 저가:{self.current_candle['low']:,} | 누적거래량:{self.current_candle['volume']:,}", end="")

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
        print("\n주문 전송을 시도합니다...")
        self.api.SendOrder(
            rqname, screen_no, acc_no, order_type, code, qty, price, hoga_gb, org_order_no
        )
        self.order_event_loop.exec_()

    def _receive_chejan_data(self, gubun, item_cnt, fid_list):
        """
        gubun 0: 주문 접수/채결, 1: 국내주식 잔고
        """
        if gubun == "0":
            order_status = self.api.GetChejanData(913) # 주문상태
            stock_code = self.api.GetChejanData(9001)[1:] # 종목코드
            order_qty = int(self.api.GetChejanData(900)) # 주문수량
            excuted_price_str = self.api.GetChejanData(910)# 체결가
            excuted_qty_str = self.api.GetChejanData(911) # 체결수량

            excuted_price = 0
            excuted_qty = 0

            if excuted_price_str:
                excuted_price = int(excuted_price_str)
            if excuted_qty_str:
                excuted_qty = int(excuted_qty_str)
                
            print(f"[주문/채결] 상태: {order_status}, 종목: {stock_code}, 주문수량: {order_qty}, 체결가: {excuted_price}, 체결수량: {excuted_qty}")
            if order_status == "접수":
                self.order_event_loop.exit()
        elif gubun == "1":
            print("잔고 변경 데이터 수신")

    def get_code_list(self, market_code):
        """
        market_code: 0: 코스피, 10: 코스닥
        """
        print(f"{'코스피' if market_code == '0' else '코스닥'} 종목 코드 목록을 요청합니다.")
        code_list_str = self.api.GetCodeListByMarket(market_code)
        code_list = code_list_str.split(';')

        return [code for code in code_list if code]
    
    def get_minute_data(self, code, tick_range=3):
        """
        tick_range = 몇분봉
        """

        print(f"[{code}] {tick_range}분봉 데이터 요청 중...")
        self.api.SetInputValue("종목코드", code)
        self.api.SetInputValue("틱범위", str(tick_range))
        self.api.SetInputValue("수정주가구분", "1")

        self.tr_data = None

        res = self.api.CommRqData("주식분봉차트조회", "opt10080", 0, "0101")

        if res != 0:
            print(f"분봉 데이터 요청 실패. 에러코드: {res}")
            return None
        
        self.tr_event_loop.exec_()
        return self.tr_data

