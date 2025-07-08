import pandas as pd
import os

def convert_csv_to_parquet():
    csv_path = "C:/program trading system/data/market_summary_features.csv"
    parquet_path = "C:/program trading system/data/market_summary.parquet"

    print(f"{csv_path}파일을 Parquet 형식을로 변환 시작...")

    try:
        df = pd.read_csv(csv_path, dtype={'code':str})
        df.to_parquet(parquet_path)
        print(f"변환 완료! '{parquet_path}'에 저장되었습니다.")
    except MemoryError:
        print("메모리 부족! 파일을 조각내어야됨")
    except Exception as e:
        print(f"변환 중 오류 발생: {e}")

if __name__ == "__main__":
    convert_csv_to_parquet()