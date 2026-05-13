import calendar
import datetime

def print_highlighted_calendar(year, month, day):
    # 달력 객체 생성 (일요일부터 시작)
    cal = calendar.TextCalendar(calendar.SUNDAY)
    
    print(f"\n      {year}년 {month}월")
    print("Su Mo Tu We Th Fr Sa")
    
    # 해당 월의 주 단위 리스트 가져오기
    month_days = cal.monthdayscalendar(year, month)
    
    for week in month_days:
        line = ""
        for d in week:
            if d == 0:
                line += "   "
            elif d == day:
                # ANSI 코드를 사용하여 해당 날짜를 빨간색 굵은 글씨로 강조 (\033[1;31m)
                line += f"\033[1;31m{d:2}\033[0m "
            else:
                line += f"{d:2} "
        print(line)

if __name__ == "__main__":
    year, month, day = 2032, 11, 6
    print_highlighted_calendar(year, month, day)