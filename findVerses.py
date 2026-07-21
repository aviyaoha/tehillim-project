from flask import Flask, render_template_string, request, jsonify
import re
import os
import urllib.request
import urllib.parse
import json

app = Flask(__name__)

# המרת אותיות עבריות (גימטריה) למספרים עבור ה-API של ספריא
HEBREW_NUMERALS = {
    'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5, 'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9,
    'י': 10, 'כ': 20, 'ל': 30, 'מ': 40, 'נ': 50, 'ס': 60, 'ע': 70, 'פ': 80, 'צ': 90,
    'ק': 100, 'ר': 200, 'ש': 300, 'ת': 400,
    'ך': 20, 'ם': 40, 'ן': 50, 'ף': 80, 'ץ': 90
}

def hebrew_to_int(hebrew_str):
    total = 0
    for char in hebrew_str:
        if char in HEBREW_NUMERALS:
            total += HEBREW_NUMERALS[char]
    return total if total > 0 else 1

# פונקציה להמרת מספרים לאותיות עבריות (גימטריה)
def int_to_hebrew(num):
    if not isinstance(num, int) or num <= 0:
        return str(num)
        
    hebrew_letters = []
    
    # מאות
    h = num // 100
    if h > 0:
        hundreds_map = {1: 'ק', 2: 'ר', 3: 'ש', 4: 'ת'}
        hebrew_letters.append(hundreds_map.get(h, ''))
        num %= 100
        
    # עשרות ויחידות
    if num == 15:
        hebrew_letters.append('ט')
        hebrew_letters.append('ו')
    elif num == 16:
        hebrew_letters.append('ט')
        hebrew_letters.append('ז')
    else:
        t = (num // 10) * 10
        u = num % 10
        tens_map = {10: 'י', 20: 'כ', 30: 'ל', 40: 'מ', 50: 'נ', 60: 'ס', 70: 'ע', 80: 'פ', 90: 'צ'}
        units_map = {1: 'א', 2: 'ב', 3: 'ג', 4: 'ד', 5: 'ה', 6: 'ו', 7: 'ז', 8: 'ח', 9: 'ט'}
        
        if t in tens_map:
            hebrew_letters.append(tens_map[t])
        if u in units_map:
            hebrew_letters.append(units_map[u])
            
    raw_str = "".join(hebrew_letters)
    if not raw_str:
        return str(num)
        
    if len(raw_str) == 1:
        return raw_str + "'"
    else:
        return raw_str[:-1] + '"' + raw_str[-1]

BOOK_MAPPING = {
    "בראשית": "Genesis", "שמות": "Exodus", "ויקרא": "Leviticus", "במדבר": "Numbers", "דברים": "Deuteronomy",
    "יהושע": "Joshua", "שופטים": "Judges", "שמואל א": "I Samuel", "שמואל ב": "II Samuel",
    "מלכים א": "I Kings", "מלכים ב": "II Kings", "ישעיהו": "Isaiah", "ירמיהו": "Jeremiah", "יחזקאל": "Ezekiel",
    "הושע": "Hosea", "יואל": "Joel", "עמוס": "Amos", "עובדיה": "Obadiah", "יונה": "Jonah", "מיכה": "Micah",
    "נחום": "Nahum", "חבקוק": "Habakkuk", "צפניה": "Zephaniah", "חגי": "Haggai", "זכריה": "Zechariah", "מלאכי": "Malachi",
    "תהילים": "Psalms", "משלי": "Proverbs", "איוב": "Job", "שיר השירים": "Song of Songs", "רות": "Ruth",
    "איכה": "Lamentations", "קהלת": "Ecclesiastes", "אסתר": "Esther", "דניאל": "Daniel", "עזרא": "Ezra",
    "נחמיה": "Nehemiah", "דברי הימים א": "I Chronicles", "דברי הימים ב": "II Chronicles"
}

TEHILLIM_DAILY_MAP = {
    1: {"label": "פרקים א' - ט'", "chapters": list(range(1, 10)), "v_range": None},
    2: {"label": "פרקים י' - י\"ז", "chapters": list(range(10, 18)), "v_range": None},
    3: {"label": "פרקים י\"ח - כ\"ב", "chapters": list(range(18, 23)), "v_range": None},
    4: {"label": "פרקים כ\"ג - כ\"ח", "chapters": list(range(23, 29)), "v_range": None},
    5: {"label": "פרקים כ\"ט - ל\"ד", "chapters": list(range(29, 35)), "v_range": None},
    6: {"label": "פרקים ל\"ה - ל\"ח", "chapters": list(range(35, 39)), "v_range": None},
    7: {"label": "פרקים ל\"ט - מ\"ג", "chapters": list(range(39, 44)), "v_range": None},
    8: {"label": "פרקים מ\"ד - מ\"ח", "chapters": list(range(44, 49)), "v_range": None},
    9: {"label": "פרקים מ\"ט - נ\"ד", "chapters": list(range(49, 55)), "v_range": None},
    10: {"label": "פרקים נ\"ה - נ\"ט", "chapters": list(range(55, 60)), "v_range": None},
    11: {"label": "פרקים ס' - ס\"ה", "chapters": list(range(60, 66)), "v_range": None},
    12: {"label": "פרקים ס\"ו - ס\"ח", "chapters": list(range(66, 69)), "v_range": None},
    13: {"label": "פרקים ס\"ט - ע\"א", "chapters": list(range(69, 72)), "v_range": None},
    14: {"label": "פרקים ע\"ב - ע\"ו", "chapters": list(range(72, 77)), "v_range": None},
    15: {"label": "פרקים ע\"ז - ע\"ח", "chapters": list(range(77, 79)), "v_range": None},
    16: {"label": "פרקים ע\"ט - פ\"ב", "chapters": list(range(79, 83)), "v_range": None},
    17: {"label": "פרקים פ\"ג - פ\"ז", "chapters": list(range(83, 88)), "v_range": None},
    18: {"label": "פרקים פ\"ח - פ\"ט", "chapters": list(range(88, 90)), "v_range": None},
    19: {"label": "פרקים צ' - צ\"ו", "chapters": list(range(90, 97)), "v_range": None},
    20: {"label": "פרקים צ\"ז - ק\"ג", "chapters": list(range(97, 104)), "v_range": None},
    21: {"label": "פרקים ק\"ד - ק\"ה", "chapters": list(range(104, 106)), "v_range": None},
    22: {"label": "פרקים ק\"ו - ק\"ז", "chapters": list(range(106, 108)), "v_range": None},
    23: {"label": "פרקים ק\"ח - קי\"ב", "chapters": list(range(108, 113)), "v_range": None},
    24: {"label": "פרקים קי\"ג - קי\"ח", "chapters": list(range(113, 119)), "v_range": None},
    25: {"label": "פרק קי\"ט (פסוקים א' - צ\"ו)", "chapters": [119], "v_range": (1, 96)},
    26: {"label": "פרק קי\"ט (פסוקים צ\"ז - קע\"ו)", "chapters": [119], "v_range": (97, 176)},
    27: {"label": "פרקים קכ' - קל\"ד", "chapters": list(range(120, 135)), "v_range": None},
    28: {"label": "פרקים קל\"ה - קל\"ט", "chapters": list(range(135, 140)), "v_range": None},
    29: {"label": "פרקים קמ' - קמ\"ד", "chapters": list(range(140, 145)), "v_range": None},
    30: {"label": "פרקים קמ\"ה - קנ'", "chapters": list(range(145, 151)), "v_range": None}
}

def clean_text(text):
    cleaned = re.sub(r'[\u0591-\u05C7]', '', text)
    cleaned = re.sub(r'\([^)]*\)', '', cleaned)
    cleaned = re.sub(r'<[^>]*>', '', cleaned)
    cleaned = re.sub(r'[:\-\.\,"\';\{\}\[\]_]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def load_and_index_tanach(file_path='Tanach.html'):
    index = {}
    tehillim_by_chapter = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"שגיאה: הקובץ '{file_path}' לא נמצא בתיקייה.")
        return {}, {}

    pattern = r'\[([^\]]+)\]([^\[]+)'
    matches = re.findall(pattern, html_content)

    for meta_info, verse_text in matches:
        meta_info = meta_info.strip()
        if ' ' in meta_info:
            book_name, location = meta_info.rsplit(' ', 1)
            if ',' in location:
                chapter_num, verse_num = location.split(',', 1)
            else:
                continue
        else:
            continue

        verse_text = re.sub(r'<[^>]*>', '', verse_text)
        verse_text = re.sub(r'\{[פסש]\}\s*$', '', verse_text).strip()

        if book_name == "תהילים":
            ch_int = hebrew_to_int(chapter_num)
            v_int = hebrew_to_int(verse_num)
            if ch_int not in tehillim_by_chapter:
                tehillim_by_chapter[ch_int] = []
            tehillim_by_chapter[ch_int].append({
                'verse_int': v_int,
                'verse_heb': verse_num,
                'text': verse_text
            })

        pure_text = clean_text(verse_text)
        if not pure_text:
            continue

        first_char = pure_text[0]
        last_char = pure_text[-1]
        key = (first_char, last_char)

        verse_info = {
            'text': verse_text,
            'book': book_name,
            'chapter': chapter_num,
            'verse': verse_num
        }

        if key not in index:
            index[key] = []
        index[key].append(verse_info)

    return index, tehillim_by_chapter

print("מאנדקס את כל כ\"ד ספרי התנ\"ך...")
tanach_index, tehillim_db = load_and_index_tanach()
print("האינדוקס הושלם!")

def get_today_tehillim_info():
    try:
        url = "https://www.hebcal.com/converter?cfg=json&g2h=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            day = data.get('hd', 1)
            hebrew_date_str = data.get('hebrew', 'יום בחודש העברי')
    except Exception as e:
        print(f"שגיאה במשיכת תאריך עברי: {e}")
        day = 1
        hebrew_date_str = "יום בחודש העברי"

    daily_info = TEHILLIM_DAILY_MAP.get(day, TEHILLIM_DAILY_MAP[1])
    portion_label = daily_info["label"]
    chapters = daily_info["chapters"]
    v_range = daily_info["v_range"]

    content = []
    for ch in chapters:
        raw_verses = tehillim_db.get(ch, [])
        filtered_verses = []
        for v in raw_verses:
            if v_range:
                if v_range[0] <= v['verse_int'] <= v_range[1]:
                    filtered_verses.append(v)
            else:
                filtered_verses.append(v)
        
        if filtered_verses:
            content.append({
                'chapter_heb': int_to_hebrew(ch), # המרת מספר הפרק לאותיות עבריות
                'verses': filtered_verses
            })

    return hebrew_date_str, portion_label, content

@app.route('/get_commentary')
def get_commentary():
    book = request.args.get('book')
    chapter = request.args.get('chapter')
    verse = request.args.get('verse')

    book_eng = BOOK_MAPPING.get(book)
    if not book_eng:
        return jsonify({'commentary': 'לא נמצא פירוש בספריא עבור ספר זה.'})

    ch_num = hebrew_to_int(chapter) if not str(chapter).isdigit() else int(chapter)
    v_num = hebrew_to_int(verse) if not str(verse).isdigit() else int(verse)

    ref = f"Rashi_on_{book_eng}.{ch_num}.{v_num}"
    url = f"https://www.sefaria.org/api/v3/texts/{urllib.parse.quote(ref)}?version=hebrew"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            versions = data.get('versions', [])
            commentary_list = []
            
            for v in versions:
                if v.get('language') == 'he' and v.get('text'):
                    commentary_list = v.get('text')
                    break

            if not commentary_list and 'text' in data:
                commentary_list = data.get('text')

            if isinstance(commentary_list, list) and len(commentary_list) > 0:
                cleaned_comments = []
                for c in commentary_list:
                    if isinstance(c, str) and c.strip():
                        clean_c = re.sub(r'<[^>]*>', '', c)
                        cleaned_comments.append(clean_c)
                
                if cleaned_comments:
                    return jsonify({'commentary': "<br><br>".join(cleaned_comments)})
            elif isinstance(commentary_list, str) and commentary_list.strip():
                return jsonify({'commentary': re.sub(r'<[^>]*>', '', commentary_list)})

    except Exception as e:
        print(f"שגיאה ב-API של ספריא: {e}")

    return jsonify({'commentary': 'אין פירוש רש"י לפסוק זה.'})

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>מציאת פסוק לפי שם - כל התנ"ך</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #f4f6f9; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 650px; margin: 40px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h1 { text-align: center; color: #2c3e50; margin-bottom: 5px; font-size: 24px; }
        h2 { text-align: center; color: #7f8c8d; font-size: 14px; margin-bottom: 20px; font-weight: normal; }
        
        .daily-tehillim-card {
            background: #f0f7ff;
            border: 1px solid #cce3f9;
            border-radius: 10px;
            padding: 18px;
            text-align: center;
            margin-bottom: 25px;
        }
        .daily-date { font-size: 13px; color: #2980b9; font-weight: bold; margin-bottom: 4px; }
        .daily-portion { font-size: 17px; color: #2c3e50; font-weight: bold; margin-bottom: 10px; }
        
        .toggle-tehillim-btn {
            background-color: #2980b9;
            color: white;
            border: none;
            padding: 9px 18px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            transition: background 0.2s;
        }
        .toggle-tehillim-btn:hover { background-color: #1f6391; }

        .daily-tehillim-content {
            margin-top: 15px;
            text-align: right;
            background: #ffffff;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #d0e3f0;
            max-height: 400px;
            overflow-y: auto;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.03);
        }
        .tehillim-chapter-title {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 4px;
            margin-top: 15px;
            margin-bottom: 10px;
            font-size: 18px;
            font-weight: bold;
        }
        .tehillim-chapter-text { font-size: 16px; line-height: 1.8; color: #2c3e50; }
        .v-num { color: #e67e22; font-weight: bold; font-size: 14px; }

        .search-form { display: flex; gap: 10px; margin-bottom: 30px; }
        input[type="text"] { flex: 1; padding: 12px 15px; border: 2px solid #ccc; border-radius: 8px; font-size: 16px; outline: none; }
        input[type="text"]:focus { border-color: #3498db; }
        button[type="submit"] { padding: 12px 25px; background-color: #3498db; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
        button[type="submit"]:hover { background-color: #2980b9; }
        
        .results-info { font-weight: bold; margin-bottom: 15px; color: #7f8c8d; }
        .verse-card { background: #fdfefe; border-right: 4px solid #2ecc71; padding: 15px; margin-bottom: 15px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .verse-meta { font-size: 13px; color: #e67e22; font-weight: bold; margin-bottom: 5px; }
        .verse-text { font-size: 18px; line-height: 1.6; color: #2c3e50; font-weight: 600; }
        
        .action-buttons { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
        .toggle-btn { background: #f39c12; color: white; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold; }
        .toggle-btn:hover { background: #d35400; }
        
        .whatsapp-btn { background: #25D366; color: white; border: none; padding: 8px 14px; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; display: inline-flex; align-items: center; }
        .whatsapp-btn:hover { background: #128C7E; }

        .commentary-box { margin-top: 10px; padding: 12px; background-color: #fcf8e3; border: 1px solid #faebcc; border-radius: 6px; font-size: 14px; color: #8a6d3b; display: none; line-height: 1.5; }
        .no-results { text-align: center; color: #e74c3c; font-size: 16px; margin-top: 20px; }
    </style>
</head>
<body>
<div class="container">
    <h1>מצא פסוק בתנ"ך לפי שם</h1>
    <h2>חיפוש מהיר בכל כ"ד הספרים</h2>
    
    <div class="daily-tehillim-card">
        <div class="daily-date">📅 תהילים יומי - {{ today_hebrew_date }}</div>
        <div class="daily-portion">הפרקים להיום: {{ today_tehillim_portion }}</div>
        <button type="button" class="toggle-tehillim-btn" onclick="toggleDailyTehillim()">📖 הצג את פרקי התהילים של היום</button>
        
        <div id="daily-tehillim-text-box" class="daily-tehillim-content" style="display: none;">
            {% for ch_data in today_tehillim_content %}
                <div class="tehillim-chapter-title">פרק {{ ch_data.chapter_heb }}</div>
                <div class="tehillim-chapter-text">
                    {% for v in ch_data.verses %}
                        <span class="v-num">({{ v.verse_heb }})</span> {{ v.text }} &nbsp;
                    {% endfor %}
                </div>
            {% endfor %}
        </div>
    </div>
    
    <form class="search-form" method="POST" action="/">
        <input type="text" name="name" placeholder="הכנס שם (למשל: שיר, אברהם...)" value="{{ user_input }}" required autocomplete="off">
        <button type="submit">חפש</button>
    </form>
    
    {% if searched %}
        {% if results %}
            <div class="results-info">נמצאו {{ results|length }} פסוקים מתאימים עבור האותיות '{{ start_letter }}' ו-'{{ end_letter }}':</div>
            {% for item in results %}
                <div class="verse-card">
                    <div class="verse-meta">{{ item.book }} • פרק {{ item.chapter }}, פסוק {{ item.verse }}</div>
                    <div class="verse-text">"{{ item.text }}"</div>
                    
                    <div class="action-buttons">
                        <button type="button" class="toggle-btn" onclick="loadCommentary(this, '{{ item.book }}', '{{ item.chapter }}', '{{ item.verse }}')">📜 הצג פירוש רש"י</button>
                        
                        <button type="button" class="whatsapp-btn" 
                                data-name="{{ user_input }}" 
                                data-text="{{ item.text }}" 
                                data-book="{{ item.book }}" 
                                data-chapter="{{ item.chapter }}" 
                                data-verse="{{ item.verse }}" 
                                onclick="shareWhatsApp(this)">
                            💬 שלח לחבר בוואטסאפ
                        </button>
                    </div>

                    <div class="commentary-box"></div>
                </div>
            {% endfor %}
        {% else %}
            <div class="no-results">לא נמצאו פסוקים מתאימים בתנ"ך עבור האותיות '{{ start_letter }}' ו-'{{ end_letter }}'.</div>
        {% endif %}
    {% endif %}
</div>

<script>
function toggleDailyTehillim() {
    const box = document.getElementById('daily-tehillim-text-box');
    const btn = document.querySelector('.toggle-tehillim-btn');
    if (box.style.display === 'none' || box.style.display === '') {
        box.style.display = 'block';
        btn.innerText = '📖 הסתר את פרקי התהילים של היום';
    } else {
        box.style.display = 'none';
        btn.innerText = '📖 הצג את פרקי התהילים של היום';
    }
}

function shareWhatsApp(btn) {
    const name = btn.getAttribute('data-name');
    const text = btn.getAttribute('data-text');
    const book = btn.getAttribute('data-book');
    const chapter = btn.getAttribute('data-chapter');
    const verse = btn.getAttribute('data-verse');
    
    const msg = `היי ${name}! 👋\nמצאתי את הפסוק שלך בתנ"ך:\n\n"${text}"\n(${book} פרק ${chapter}, פסוק ${verse})`;
    const url = `https://wa.me/?text=${encodeURIComponent(msg)}`;
    window.open(url, '_blank');
}

function loadCommentary(btn, book, chapter, verse) {
    const box = btn.parentElement.nextElementSibling;
    
    if (box.style.display === 'block') {
        box.style.display = 'none';
        btn.innerText = '📜 הצג פירוש רש"י';
        return;
    }
    
    if (box.dataset.loaded === 'true') {
        box.style.display = 'block';
        btn.innerText = '📜 הסתר פירוש רש"י';
        return;
    }

    btn.innerText = '⏳ טוען פירוש...';
    
    fetch('/get_commentary?book=' + encodeURIComponent(book) + '&chapter=' + encodeURIComponent(chapter) + '&verse=' + encodeURIComponent(verse))
        .then(res => res.json())
        .then(data => {
            box.innerHTML = '<strong>פירוש רש"י:</strong><br>' + data.commentary;
            box.style.display = 'block';
            box.dataset.loaded = 'true';
            btn.innerText = '📜 הסתר פירוש רש"י';
        })
        .catch(err => {
            box.innerHTML = 'שגיאה בטעינת הפירוש. נסה שוב מאוחר יותר.';
            box.style.display = 'block';
            btn.innerText = '📜 הצג פירוש רש"י';
        });
}
</script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    results = []
    user_input = ""
    searched = False
    start_letter = ""
    end_letter = ""

    today_hebrew_date, today_tehillim_portion, today_tehillim_content = get_today_tehillim_info()

    if request.method == 'POST':
        user_input = request.form.get('name', '').strip()
        cleaned_name = clean_text(user_input)
        
        if len(cleaned_name) >= 2:
            searched = True
            start_letter = cleaned_name[0]
            end_letter = cleaned_name[-1]
            results = tanach_index.get((start_letter, end_letter), [])

    return render_template_string(
        HTML_TEMPLATE, 
        results=results, 
        user_input=user_input, 
        searched=searched, 
        start_letter=start_letter, 
        end_letter=end_letter,
        today_hebrew_date=today_hebrew_date,
        today_tehillim_portion=today_tehillim_portion,
        today_tehillim_content=today_tehillim_content
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
