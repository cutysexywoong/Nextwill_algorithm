import calendar
import datetime

def print_highlighted_calendar(year, month, day):
    """지정된 연도/월의 달력을 출력하고 특정 날짜를 강조합니다."""
    try:
        cal = calendar.TextCalendar(calendar.SUNDAY)
        
        print(f"\n      {year}년 {month}월")
        print("Su Mo Tu We Th Fr Sa")
        
        month_days = cal.monthdayscalendar(year, month)
        
        for week in month_days:
            line = ""
            for d in week:
                if d == 0:
                    line += "   "
                elif d == day:
                    # ANSI 코드를 사용하여 해당 날짜를 빨간색 배경으로 강조 (\033[41m)
                    line += f"\033[1;31m{d:2}\033[0m "
                else:
                    line += f"{d:2} "
            print(line)
    except Exception as e:
        print(f"달력을 생성하는 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    print("=== 생일 달력 확인 도구 v3 ===")
    try:
        # 사용자로부터 데이터 입력 받기
        birth_input = input("본인의 생일을 입력하세요 (예: 2002-11-06): ")
        birth_date = datetime.datetime.strptime(birth_input, "%Y-%m-%d")
        
        target_year = int(input("확인하고 싶은 연도를 입력하세요: "))
        print_highlighted_calendar(target_year, birth_date.month, birth_date.day)
    except ValueError:
        print("입력 형식이 잘못되었습니다. YYYY-MM-DD 형식을 지켜주세요.")