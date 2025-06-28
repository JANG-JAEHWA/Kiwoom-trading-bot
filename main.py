import sys
from PyQt5.QtWidgets import QApplication
from kiwoom_api import KiwoomAPI
from strategy import simple_ma_strategy

def main():
    print("자동매매 프로그램 시작")
    
    
    kiwoom = KiwoomAPI()
    kiwoom.login()
    print(f"로그인 후 확인된 계좌번호: {kiwoom.account_number}")
    
    samsung_data = kiwoom.get_daily_data("005930")

    if samsung_data:
        print(f"총 {len(samsung_data)}일치의 데이터를 수신했습니다.")
        print("최신 5일치 데이터:")
        for i, day_data in enumerate(samsung_data[:5]):
            print(f" 날짜: {day_data['date']}, 종가: {day_data['close']:,}원, 거래량: {day_data['volume']:,}")

        signal = simple_ma_strategy(samsung_data)

        print(f"\n[최종 판단] 매매 전략 신호: {signal}")
        if signal == 'BUY':
            print("매수 준비합니다.")
        else:
            print("매수 조건이 총족되지 않았습니다.")
    else:
        print("데이터를 가져오는 데 실패했습니다.")
    print("\n모든 테스트가 완료되었습니다.")

if __name__ == "__main__":
    app = QApplication(sys.argv) #PyQt5 생성
    main()
    
