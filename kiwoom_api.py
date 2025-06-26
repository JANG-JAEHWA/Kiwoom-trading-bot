import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop

class KiwoomAPI:
    def __init__(self):
        self.api = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self._set_event_handlers()
        self.login_event_loop = QEventLoop()
        self.tr_event_loop = QEventLoop()
        self.tr_data = None
        self.account_number = None

    def _set_event_handlers(self):
        """이벤트와 이벤트 핸들러를 연결합니다."""
        self.api.OnEventConnect.connect(self._event_connect)
        self.api.OnReceiveTrData.connect(self._recieve_tr_data)

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
            print("로그인에 성공했습니다.")
            account_numbers = self.api.GetLoginInfo("ACCNO")
            self.account_number = account_numbers.split(';')[0]
            print(f"성공적으로 계좌번호를 가져왔습니다: {self.account_number}")
        else:
            print(f"로그인에 실패했습니다. 에러 코드: {err_code}")

        self.login_event_loop.exit()

    def get_daily_data(self, code, data_str="20250625"):
        """
        지정한 종목의 일봉 데이터를 요청합니다.
        TR 코드: opt10081
        """
        print(f"[{code}] 일봉 데이터 요청 중...")
        
        self.api.SetInputValue("종목코드", code)
        self.api.SetInputValue("기준일자", data_str)
        self.api.SetInputValue("수정주가구분", "1")#1: 수정주가, 0: 원주가

        self.api.CommRqData("일봉데이터요청", "opt10081", 0, "0101")

        self.tr_event_loop.exec_()

        return self.tr_data

    def _recieve_tr_data(self, screen_no, rqname, trcode, record_name, prev_next, *args):
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
                    'volume': int(self.api.GetCommData(trcode, rqname, i, "일자").strip())
                }
                data_list.append(data)
            self.tr_data = data_list
        self.tr_event_loop.exit()
                    
