import subprocess
import os
import sys

def run_script(script_path, python_executable):
    try:
        print(f"\n--- [실행 시작] {os.path.basename(script_path)} ---")
        script_dir = os.path.dirname(script_path)
        subprocess.run([python_executable, script_path], check=True, cwd=script_dir)
        print(f"\n--- [실행 성공] {os.path.basename(script_path)} ---")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n--- [실행 실패] {os.path.basename(script_path)} -오류: {e}")
        return False
    except FileNotFoundError:
        print(f"!!! [실행 실패] 파이썬 실행 파일을 찾을 수 없습니다: {python_executable}")
        return False

def main():
    print("="*50)
    print("  AI 자동매매 시스템 일일 작전 준비 자동 실행")
    print("="*50)
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    py32_path = "C:/Users/pc/AppData/Local/Programs/Python/Python39-32/python.exe"
    py64_path = "C:/Users/pc/AppData/Local/Programs/Python/Python313/python.exe"


    scripts_to_run = {
        "데이터 최신화": (os.path.join(project_root, "trader_bot_32bit", "update_data.py"), py32_path),
        "데이터 전처리": (os.path.join(project_root, "ai_research_64bit", "preprocess_data.py"), py64_path),
        "스카우터 라벨링": (os.path.join(project_root, "ai_research_64bit", "label_data.py"), py64_path),
        "스카우터 훈련": (os.path.join(project_root, "ai_research_64bit", "train_scout_daily.py"), py64_path),
        "전략가 라벨링": (os.path.join(project_root, "ai_research_64bit", "label_strategy_data.py"), py64_path),
        "전략가 및 atr 배수 찾기훈련": (os.path.join(project_root, "ai_research_64bit", "train_strategist_daily.py"), py64_path),
    }

    for task_name, (script_path, python_exec) in scripts_to_run.items():
        print(f"\n>> 단계: {task_name}")
        if not run_script(script_path, python_exec):
            print("\n!!! 이전 단계에서 오류가 발생하여 작전 준비를 중단합니다. !!!")
            return

    print("\n\n" + "="*50)
    print("  모든 작전 준비가 완료되었습니다. 실전 매매 가능!")
    print("="*50)

if __name__ == "__main__":
    main()
