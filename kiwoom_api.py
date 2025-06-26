import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop

class KiwoomAPI:
    def __init__(self):
        self.api = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self._set_event_handlers()
        self.login_event_loop = QEventLoop()
        self.account_number = None

    def _set_event_handlers(self):
        """이벤트와 이벤트 핸들러를 연결합니다."""
        self.api.OnEventConnect.connect(self._event_connect)

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
