from flask import Flask, render_template_string, request
import re
import os

app = Flask(__name__)

# פונקציית ניקוי הטקסט המצוינת שלך
def clean_text(text):
    # הסרת ניקוד וטעמי מקרא
    cleaned = re.sub(r'[\u0591-\u05C7]', '', text)
    # הסרת סוגריים עגולים ותוכן בתוכם (כמו קרי וכתיב)
    cleaned = re.sub(r'\([^)]*\)', '', cleaned)
    # הסרת סימני פיסוק, סוגריים מסולסלים או מרובעים ותגיות HTML שנשארו
    cleaned = re.sub(r'<[^>]*>', '', cleaned)
    cleaned = re.sub(r'[:\-\.\,"\';\{\}\[\]_]', '', cleaned)
    # החלפת רווחים כפולים ברווח בודד
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

# פונקציה חכמה לקריאה ואינדוקס של כל התנ"ך מקובץ ה-HTML
def load_and_index_tanach(file_path='Tanach.html'):
    index = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"שגיאה: הקובץ '{file_path}' לא נמצא בתיקייה.")
        return {}

    # ביטוי רגולרי שמחפש את הפורמט: [שם_ספר פרק,פסוק] ואז את הטקסט עד לסוגריים המרובעים הבאים
    # למשל: [בראשית א,א] בראשית ברא...
    pattern = r'\[([^\]]+)\]([^\[]+)'
    matches = re.findall(pattern, html_content)

    for meta_info, verse_text in matches:
        # meta_info מכיל למשל "בראשית א,א" או "תהילים קנ,ו"
        meta_info = meta_info.strip()
        
        # פירוק לשם הספר, ולפרק+פסוק
        # נחלק לפי הרווח האחרון (כדי לתמוך בספרים כמו "דברי הימים א")
        if ' ' in meta_info:
            book_name, location = meta_info.rsplit(' ', 1)
            if ',' in location:
                chapter_num, verse_num = location.split(',', 1)
            else:
                continue
        else:
            continue

        # ניקוי הטקסט הגולמי של הפסוק מתגיות HTML שנשארו (כמו <br> או תגיות סגירה)
        verse_text = re.sub(r'<[^>]*>', '', verse_text)
        # הסרת סימוני פרשיות כמו {פ} או {ס} שמופיעים בסוף הפסוקים בקובץ ה-HTML
        verse_text = re.sub(r'\{[פסש]\}\s*$', '', verse_text).strip()
        verse_text = verse_text.strip()

        # ניקוי סופי לבדיקת אות פותחת וסוגרת
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

# הפעלת האינדוקס של כל התנ"ך (קורה פעם אחת כשהשרת נדלק)
print("מאנדקס את כל כ\"ד ספרי התנ\"ך... אנא המתן...")
tanach_index = load_and_index_tanach()
print(f"האינדוקס הושלם! נטענו בהצלחה פסקאות ופסוקים מכל התנ\"ך.")

# ה-HTML המעודכן - תומך באנטר ומציג גם את שם הספר (חומש/נ"ך)
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
        button { padding: 12px 25px; background-color: #3498db; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
        button:hover { background-color: #2980b9; }
        .results-info { font-weight: bold; margin-bottom: 15px; color: #7f8c8d; }
        .verse-card { background: #fdfefe; border-right: 4px solid #2ecc71; padding: 15px; margin-bottom: 15px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .verse-meta { font-size: 13px; color: #e67e22; font-weight: bold; margin-bottom: 5px; }
        .verse-text { font-size: 18px; line-height: 1.6; color: #2c3e50; }
        .no-results { text-align: center; color: #e74c3c; font-size: 16px; margin-top: 20px; }
    </style>
</head>
<body>
<div class="container">
    <h1>מצא פסוק בתנ"ך לפי שם</h1>
    <h2>חיפוש מהיר בכל כ"ד הספרים (חומש, נביאים וכתובבים)</h2>
    
    <!-- שימוש בטופס סטנדרטי המאפשר למקש אנטר לעבוד אוטומטית ובאופן טבעי -->
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
                </div>
            {% endfor %}
        {% else %}
            <div class="no-results">לא נמצאו פסוקים מתאימים בתנ"ך עבור האותיות '{{ start_letter }}' ו-'{{ end_letter }}'.</div>
        {% endif %}
    {% endif %}
</div>
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