from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QObject, QEventLoop, QTimer

class KiwoomAPICollector(QObject):
    def __init__(self):
        super().__init__()
        self.api = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.api.OnEventConnect.connect(self._event_connect)
        self.api.OnReceiveTrData.connect(self._receive_tr_data)
        self.login_event_loop = QEventLoop()
        self.tr_event_loop = None
        self.tr_event_loop = None
        self.prev_next = "0"
    
    def login(self): self.api.CommConnect(); self.login_event_loop.exec_()
    def _event_connect(self, err_code): self.login_event_loop.exit()
    def get_code_list(self, market_code): return self.api.GetCodeListByMarket(market_code).split(';')[:-1]

    def get_minute_data_page(self, code, tick_range=3, is_continuous=False):
        self.tr_event_loop = QEventLoop()

        self.tr_data = None
        self.api.SetInputValue("종목코드", code)
        self.api.SetInputValue("틱범위", "3")
        self.api.SetInputValue("수정주가구분", "1")

        self.api.CommRqData("주식분봉차트조회", "opt10080", 2 if is_continuous else 0, "0101")
        self.tr_event_loop.exec_()
        return self.tr_data, self.prev_next
    
    def _receive_tr_data(self, screen_no, rqname, trcode, rec_name, prev_next, *args):
        self.prev_next = prev_next
        if rqname == "주식분봉차트조회":
            count = self.api.GetRepeatCnt(trcode, rqname)
            data_list =[]
            for i in range(count):
                try:
                    item = {
                        'date': self.api.GetCommData(trcode, rqname, i, "체결시간").strip(),
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
        if self.tr_event_loop and self.tr_event_loop.isRunning():
            self.tr_event_loop.exit()

    def get_connect_state(self):
        return self.api.GetConnectState() #0-미연결, 1-연결