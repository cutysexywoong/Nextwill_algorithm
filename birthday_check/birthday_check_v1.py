import datetime

def get_birthday_weekday(year, month, day):
    target_date = datetime.date(year, month, day)
    days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    return days[target_date.weekday()]

if __name__ == "__main__":
    year, month, day = 2032, 11, 6
    weekday = get_birthday_weekday(year, month, day)
    print(f"{year}년 {month}월 {day}일은 {weekday}입니다.")