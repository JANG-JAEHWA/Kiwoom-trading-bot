from train_scout import run_scout_and_get_recommendations
from train_ai import train_ai_model
from backtester import run_backtest
import os
import joblib

def run_full_simulation():
    print("="*50)
    print("AI 트레이닝 시스템 전체 시뮬레이션을 시작합니다.")
    print("="*50)

    print("\n[단계 1] AI 스카우터가 유망 종목을 선정합니다...")
    recommended_codes = run_scout_and_get_recommendations()

    if not recommended_codes:
        print("\n시뮬레이션을 종료합니다.")
        return
    all_profits = []

    for raw_code in recommended_codes:
        code = raw_code.split('_')[0]
        print("\n" + "="*50)
        print(f"[단계 2] 추천 종목 '{code}'에 대한 전략 수립 및 백테스팅을 시작합니다.")
        print("="*50)

        stock_data_path = os.path.join("data", f"{code}_daily_data.csv")
        strategist_model, _ = train_ai_model(stock_data_path)

        if strategist_model is None:
            print(f"'{code}' 종목의 전략가 모델 훈련에 실패했습니다. 다음 종목으로 넘어갑니다.")
            continue

        model_dir = 'models'
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        model_path = os.path.join(model_dir, f'strategist_{code}.joblib')
        joblib.dump(strategist_model, model_path)
        print(f"'{code}' 종목을 위한 전략가 모델을 저장했습니다.: {model_path}")

        profit_rate = run_backtest(stock_data_path)
        all_profits.append(profit_rate)
    print("\n" + "="*50)
    print("[단계 3] 전체 시뮬레이션 결과 요약")
    print("="*50)
    if not all_profits:
        print("분석된 종목이 없습니다.")
    else:
        average_profit = sum(all_profits) / len(all_profits)
        print(f"총 {len(all_profits)}개 종목 분석 완료.")
        print(f"평균 수익률: {average_profit:.2f}%")

if __name__ == "__main__":
    run_full_simulation()
