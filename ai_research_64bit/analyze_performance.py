import pandas as pd
import numpy as np
import os

def analyze_performance(log_path, initial_capital=100_000_000):
    try:
        df = pd.read_csv(log_path)
    except FileNotFoundError:
        print(f"오류: 거래 로그 파일({log_path})을 찾을 수 없습니다.")
        return

    if df.empty or len(df[df['주문유형'] == '매도']) == 0:
        print("분석할 거래 내역(매도)이 없습니다.")
        return

    # --- [핵심 수정] 정확한 손익(PnL) 계산 로직 ---
    df['pnl'] = 0.0
    # 매도 기록만 순회
    for i, sell_trade in df[df['주문유형'] == '매도'].iterrows():
        # 동일한 주문번호를 가진 매수 기록을 찾음
        buy_trade = df[(df['주문번호'] == sell_trade['주문번호']) & (df['주문유형'] == '매수')]
        
        if not buy_trade.empty:
            buy_price = buy_trade.iloc[0]['체결가격']
            buy_qty = buy_trade.iloc[0]['체결수량']
            
            sell_price = sell_trade['체결가격']
            sell_qty = sell_trade['체결수량']

            # 수수료/세금을 대략적으로 양쪽에 0.3%씩 적용
            profit = (sell_price * sell_qty * 0.997) - (buy_price * buy_qty * 1.003)
            df.loc[i, 'pnl'] = profit

    # --- 핵심 성과 지표 계산 ---
    total_pnl = df['pnl'].sum()
    profit_rate = (total_pnl / initial_capital) * 100
    
    sell_trades = df[df['주문유형'] == '매도']
    
    # [수정] win_rate 계산 버그 수정
    win_rate = (len(sell_trades[sell_trades['pnl'] > 0]) / len(sell_trades)) * 100 if len(sell_trades) > 0 else 0
    
    avg_profit = sell_trades[sell_trades['pnl'] > 0]['pnl'].mean()
    # [수정] avg_loss 계산 버그 수정
    avg_loss = abs(sell_trades[sell_trades['pnl'] < 0]['pnl'].mean())
    
    profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else float('inf')

    # 자산 변화 곡선 및 MDD 계산
    df['capital'] = initial_capital + df['pnl'].cumsum()
    peak = df['capital'].cummax()
    drawdown = (df['capital'] - peak) / peak
    max_drawdown = abs(drawdown.min()) * 100

    print("\n" + "="*30)
    print("      AI 트레이딩 성과 분석")
    print("="*30)
    print(f" 총 수익률:\t\t{profit_rate:.2f}%")
    print(f" 총 손익:\t\t{total_pnl:,.0f} 원")
    print(f" 승률:\t\t\t{win_rate:.2f}%")
    print(f" 손익비:\t\t\t{profit_loss_ratio:.2f}")
    print(f" 최대 자본 낙폭 (MDD):\t-{max_drawdown:.2f}%")
    print(f" 총 거래 횟수 (매도 기준): {len(sell_trades)}")
    print("="*30)

if __name__ == "__main__":
    log_file_path = "C:/program trading system/trade_log.csv"

    analyze_performance(log_file_path)
