from flask import Flask, render_template_string, request
import re
import os

app = Flask(__name__)

def clean_text(text):
    cleaned = re.sub(r'[\u0591-\u05C7]', '', text)
    cleaned = re.sub(r'\([^)]*\)', '', cleaned)
    cleaned = re.sub(r'[:\-\.\,"\';\{\}]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def parse_gematria_header(chapter_str):
    return chapter_str.replace("פרק-", "").strip()

def load_and_index_psalms(file_path='Tehillim.txt'):
    index = {}
    current_chapter = "א"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"שגיאה: הקובץ '{file_path}' לא נמצא.")
        return {}

    for line in lines:
        line = line.strip()
        if not line or "_____" in line:
            continue
        if "תהילים פרק-" in line:
            parts = line.split("תהילים ")
            if len(parts) > 1:
                current_chapter = parse_gematria_header(parts[1])
            continue

        matches = re.findall(r'\{([^}]+)\}([^\{]+)', line)
        for verse_num_str, verse_text in matches:
            verse_num_str = verse_num_str.strip()
            verse_text = verse_text.strip()
            pure_text = clean_text(verse_text)
            
            if not pure_text:
                continue
                
            key = (pure_text[0], pure_text[-1])
            verse_info = {
                'text': verse_text,
                'chapter': current_chapter,
                'verse': verse_num_str
            }
            if key not in index:
                index[key] = []
            index[key].append(verse_info)
    return index

psalms_index = load_and_index_psalms()

# ה-HTML שמור ישירות בתוך קובץ הפייתון
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>מציאת פסוק לפי שם - ספר תהילים</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #f4f6f9; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 650px; margin: 40px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h1 { text-align: center; color: #2c3e50; margin-bottom: 30px; font-size: 24px; }
        .search-form { display: flex; gap: 10px; margin-bottom: 30px; }
        input[type="text"] { flex: 1; padding: 12px 15px; border: 2px solid #ccc; border-radius: 8px; font-size: 16px; outline: none; }
        input[type="text"]:focus { border-color: #3498db; }
        button { padding: 12px 25px; background-color: #3498db; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
        button:hover { background-color: #2980b9; }
        .results-info { font-weight: bold; margin-bottom: 15px; color: #7f8c8d; }
        .verse-card { background: #fdfefe; border-right: 4px solid #3498db; padding: 15px; margin-bottom: 15px; border-radius: 4px; }
        .verse-meta { font-size: 13px; color: #e67e22; font-weight: bold; margin-bottom: 5px; }
        .verse-text { font-size: 18px; line-height: 1.6; color: #2c3e50; }
        .no-results { text-align: center; color: #e74c3c; font-size: 16px; margin-top: 20px; }
    </style>
</head>
<body>
<div class="container">
    <h1>מצא פסוק בתהילים לפי שם</h1>
    <form class="search-form" method="POST">
        <input type="text" name="name" placeholder="הכנס שם..." value="{{ user_input }}" required autocomplete="off">
        <button type="submit">חפש</button>
    </form>
    {% if searched %}
        {% if results %}
            <div class="results-info">נמצאו {{ results|length }} פסוקים:</div>
            {% for item in results %}
                <div class="verse-card">
                    <div class="verse-meta">תהילים פרק {{ item.chapter }}, פסוק {{ item.verse }}</div>
                    <div class="verse-text">"{{ item.text }}"</div>
                </div>
            {% endfor %}
        {% else %}
            <div class="no-results">לא נמצאו פסוקים מתאימים.</div>
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
            results = psalms_index.get((start_letter, end_letter), [])

    return render_template_string(HTML_TEMPLATE, results=results, user_input=user_input, 
                                  searched=searched, start_letter=start_letter, end_letter=end_letter)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)