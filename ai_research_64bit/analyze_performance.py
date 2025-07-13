import pandas as pd
import numpy as np
import os

def analyze_performance(log_path, initial_capital=100_000_000):
    try:
        df= pd.read_csv(log_path)
    except FileNotFoundError:
        print(f"오류: 거래 로그 파일({log_path})을 찾을 수 없습니다.")

    if df.empty:
        print("분석할 거래 내역이 없습니다.")
        return
    
    df['pnl'] = 0.0
    for i in range(len(df)):
        if df.loc[i, '주문유형'] == '매도':
            buy_trade = df[df['주문번호'] == df.loc[i, '주문번호']].iloc[0]
            pnl = (df.loc[i, '체결가격'] - buy_trade['체결가격'] * buy_trade['체결수량'])
            df.loc[i, 'pnl'] = pnl
        
    total_return = df['pnl'].sum()
    profit_rate = (total_return / initial_capital) * 100

    trades = df[df['주문유형'] == '매도']
    if len(trades) == 0:
        win_rate = 0
        profit_loss_ratio = 0
    else:
        win_rate (len(trades[trades['pnl'] > 0]) / len(trades)) * 100
        avg_profit = trades[trades['pnl'] > 0]['pnl'].mean()
        avg_loss = abs(trades[trades['pnl'] > 0]['pnl'].mean())
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else float('inf')

    df['capital'] = initial_capital + df['pnl'].cumsum()
    peak = df['capital'].cummax()
    drawdown = (df['capital'] - peak) / peak
    max_drawdown = abs(drawdown.min()) * 100

    print("\n" + "="*30)
    print("     AI 트레이딩 성과 분석")
    print("="*30)
    print(f" 총 수익률:\t\t{profit_rate:.2f}%")
    print(f" 총 손익:\t\t{total_return:,.0f} 원")
    print(f" 승률:\t\t\t{win_rate:.2f}%")
    print(f" 손인비:\t\t\t{profit_loss_ratio:.2f}")
    print(f" 최대 자본 낙폭 (MDD): \t-{max_drawdown:.2f}%")
    print(f" 총 거래 횟수 (매도 기준): {len(trades)}")
    print("="*30)

if __name__ == "__main__":
    log_file_path = "C:/program trading system/trade_log.csv"

    analyze_performance(log_file_path)
