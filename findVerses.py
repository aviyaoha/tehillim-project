from flask import Flask, render_template_string, request, jsonify
import re
import os
import urllib.request
import urllib.parse
import json

app = Flask(__name__)

HEBREW_NUMERALS = {
    'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5, 'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9,
    'י': 10, 'כ': 20, 'ל': 30, 'מ': 40, 'נ': 50, 'ס': 60, 'ע': 70, 'פ': 80, 'צ': 90,
    'ק': 100, 'ר': 200, 'ש': 300, 'ת': 400
}

def hebrew_to_int(hebrew_str):
    total = 0
    for char in hebrew_str:
        if char in HEBREW_NUMERALS:
            total += HEBREW_NUMERALS[char]
    return total if total > 0 else 1

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

def clean_text(text):
    cleaned = re.sub(r'[\u0591-\u05C7]', '', text)
    cleaned = re.sub(r'\([^)]*\)', '', cleaned)
    cleaned = re.sub(r'<[^>]*>', '', cleaned)
    cleaned = re.sub(r'[:\-\.\,"\';\{\}\[\]_]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def load_and_index_tanach(file_path='Tanach.html'):
    index = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"שגיאה: הקובץ '{file_path}' לא נמצא בתיקייה.")
        return {}

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

    return index

print("מאנדקס את כל כ\"ד ספרי התנ\"ך...")
tanach_index = load_and_index_tanach()
print("האינדוקס הושלם!")

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
        h2 { text-align: center; color: #7f8c8d; font-size: 14px; margin-bottom: 30px; font-weight: normal; }
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
                        
                        <!-- כפתור שיתוף לוואטסאפ מבוסס JS למניעת תקלות מילוט -->
                        <button type="button" class="whatsapp-btn" onclick="shareWhatsApp({{ user_input|tojson }}, {{ item.text|tojson }}, {{ item.book|tojson }}, {{ item.chapter|tojson }}, {{ item.verse|tojson }})">💬 שלח לחבר בוואטסאפ</button>
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
function shareWhatsApp(name, text, book, chapter, verse) {
    const msg = `היי ${name}! 👋\nמצאתי את הפסוק שלך בתנ"ך:\n\n"${text}"\n(${book} פרק ${chapter}, פסוק ${verse})`;
    const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`;
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

    if request.method == 'POST':
        user_input = request.form.get('name', '').strip()
        cleaned_name = clean_text(user_input)
        
        if len(cleaned_name) >= 2:
            searched = True
            start_letter = cleaned_name[0]
            end_letter = cleaned_name[-1]
            results = tanach_index.get((start_letter, end_letter), [])

    return render_template_string(HTML_TEMPLATE, results=results, user_input=user_input, 
                                  searched=searched, start_letter=start_letter, end_letter=end_letter)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)