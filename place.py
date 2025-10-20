from flask import Flask, render_template, request
import pandas as pd
import random
app = Flask(__name__)
df_place = pd.read_csv("place.csv", encoding="utf-8")
df_place.columns = df_place.columns.str.strip()
category_duration = {
    "음식점": 1,
    "카페": 2,
    "쇼핑": 2,
    "술집": 3,
    "영화": 3,
    "문화생활": 1,
    "관광명소": 1
}
region_map = {
    "신촌": ["신촌", "서대문구"],
    "홍대": ["홍대", "마포"],
    "용산": ["용산"],
    "성수": ["성수"],
    "강남": ["강남"],
}
def can_fit(current_time, cat, block_end):
    return current_time + category_duration[cat] <= block_end
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/result', methods=['POST'])
def result():
    region_input = request.form.get('region', '')
    people = request.form.get('people', '')
    gender = ""
    start_time_str = request.form.get('start_time', '10:00')
    try:
        start_time = int(start_time_str.split(":")[0])
    except:
        start_time = 12
    region_keywords = region_map.get(region_input, [region_input])
    mask = df_place['address_name'].apply(lambda x: any(r in str(x) for r in region_keywords) if pd.notnull(x) else False)
    df_filtered = df_place[mask]
    current_time = max(start_time, 10)
    schedule = []
    # 컨트롤 변수
    used_sul = False
    used_movie = False
    # 음식점 고정 슬롯
    meal_slots = []
    if current_time <= 12:
        meal_slots.append(12)
    if current_time <= 18:
        meal_slots.append(18)
    # 1. 12시 전(10~12) 일정
    if 12 in meal_slots:
        pre12_end = 12
    elif 18 in meal_slots and current_time < 18:
        pre12_end = 18
    else:
        pre12_end = 24
    while current_time < pre12_end:
        block_end = min(pre12_end, 12, 18, 24)
        # 카테고리 후보
        avail_cats = []
        for c in category_duration:
            if c == "음식점":
                continue
            if c == "술집":
                continue  # 술집은 19시 이후에만
            if c == "영화" and used_movie:
                continue
            if c == "영화" and (current_time < 10 or not can_fit(current_time, "영화", block_end)):
                continue
            if not can_fit(current_time, c, block_end):
                continue
            avail_cats.append(c)
        if not avail_cats:
            break
        cat = random.choice(avail_cats)
        if cat == "영화":
            used_movie = True
        block = make_block(current_time, cat, df_filtered)
        schedule.append(block)
        current_time += category_duration[cat]
    # 2. 12시 음식점
    if 12 in meal_slots and current_time == 12:
        block = make_block(12, "음식점", df_filtered)
        schedule.append(block)
        current_time = 13
    # 3. 13~18시 일정
    if 18 in meal_slots:
        pre18_end = 18
    else:
        pre18_end = 24
    while current_time < pre18_end:
        block_end = min(pre18_end, 18, 24)
        avail_cats = []
        for c in category_duration:
            if c == "음식점":
                continue
            if c == "술집":
                continue
            if c == "영화" and used_movie:
                continue
            if c == "영화" and (current_time < 10 or not can_fit(current_time, "영화", block_end)):
                continue
            if not can_fit(current_time, c, block_end):
                continue
            avail_cats.append(c)
        if not avail_cats:
            break
        cat = random.choice(avail_cats)
        if cat == "영화":
            used_movie = True
        block = make_block(current_time, cat, df_filtered)
        schedule.append(block)
        current_time += category_duration[cat]
    # 4. 18시 음식점
    if 18 in meal_slots and current_time == 18:
        block = make_block(18, "음식점", df_filtered)
        schedule.append(block)
        current_time = 19
    # 5. 19~24시 일정 (술집은 단 1번만)
    while current_time < 24:
        block_end = 24
        avail_cats = []
        for c in category_duration:
            if c == "음식점":
                continue
            if c == "술집" and (used_sul or current_time < 19 or not can_fit(current_time, "술집", block_end)):
                continue
            if c == "영화" and (used_movie or current_time < 10 or not can_fit(current_time, "영화", block_end)):
                continue
            if not can_fit(current_time, c, block_end):
                continue
            avail_cats.append(c)
        if not avail_cats:
            break
        cat = random.choice(avail_cats)
        if cat == "술집":
            used_sul = True
        if cat == "영화":
            used_movie = True
        block = make_block(current_time, cat, df_filtered)
        schedule.append(block)
        current_time += category_duration[cat]
    return render_template(
        "result.html",
        region=region_input,
        gender=gender,
        people=people,
        start_time=start_time_str,
        schedule=schedule
    )
def make_block(hour, category, df):
    candidates = df[df["분류"].str.strip() == category]
    if not candidates.empty:
        items = candidates.sample(n=min(3, len(candidates)), replace=False)
        candidates_list = []
        for _, row in items.iterrows():
            candidates_list.append({
                "place": row.get("place_name", ""),
                "url": row.get("place_url", "#"),
                "iframe": row.get("place_url", ""),
            })
        if len(candidates_list) < 3:
            for _ in range(3 - len(candidates_list)):
                candidates_list.append({
                    "place": f"({category} 장소 없음)",
                    "url": "#",
                    "iframe": "",
                })
    else:
        candidates_list = [
            {"place": f"({category} 장소 없음)", "url": "#", "iframe": ""} for _ in range(3)
        ]
    return {
        "time": str(hour),
        "category": category,
        "candidates": candidates_list,
    }
if __name__ == '__main__':
    app.run(debug=True)
