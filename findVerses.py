import re
import webview

# פונקציות הניקוי והאינדוקס הרגילות שלך
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
            if not pure_text: continue
            key = (pure_text[0], pure_text[-1])
            if key not in index: index[key] = []
            index[key].append({'text': verse_text, 'chapter': current_chapter, 'verse': verse_num_str})
    return index

psalms_index = load_and_index_psalms()

# מחלקה (API) שמאפשרת ל-JavaScript ב-HTML לדבר עם פייתון
class Api:
    def search_name(self, name):
        cleaned_name = clean_text(name)
        if len(cleaned_name) < 2:
            return {"error": "השם חייב להכיל לפחות שתי אותיות."}
        
        start_letter = cleaned_name[0]
        end_letter = cleaned_name[-1]
        results = psalms_index.get((start_letter, end_letter), [])
        return {"results": results, "start": start_letter, "end": end_letter}

# ה-HTML המעודכן שמשתמש ב-JavaScript כדי לבקש נתונים מפייתון בלי לרענן את הדף
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #f4f6f9; padding: 20px; direction: rtl; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h1 { text-align: center; color: #2c3e50; font-size: 22px; }
        .search-form { display: flex; gap: 10px; margin-bottom: 20px; }
        input { flex: 1; padding: 12px; border: 2px solid #ccc; border-radius: 8px; font-size: 16px; }
        button { padding: 12px 20px; background-color: #3498db; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
        button:hover { background-color: #2980b9; }
        .card { background: #fdfefe; border-right: 4px solid #3498db; padding: 12px; margin-bottom: 12px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .meta { font-size: 12px; color: #e67e22; font-weight: bold; }
        .text { font-size: 17px; line-height: 1.5; color: #2c3e50; margin-top: 5px; }
    </style>
</head>
<body>
<div class="container">
    <h1>פסוקים בתהילים לפי שם</h1>
    <div class="search-form">
        <input type="text" id="nameInput" placeholder="הכנס שם...">
        <button onclick="search()">חפש</button>
    </div>
    <div id="resultsArea"></div>
</div>

<script>
    function search() {
        const name = document.getElementById('nameInput').value;
        const area = document.getElementById('resultsArea');
        area.innerHTML = "מחפש...";
        
        // קריאה לפונקציית הפייתון בצורה ישירה!
        pywebview.api.search_name(name).then(response => {
            if (response.error) {
                area.innerHTML = `<div style="color:red;">${response.error}</div>`;
                return;
            }
            if (response.results.length === 0) {
                area.innerHTML = `<div>לא נמצאו פסוקים עבור האותיות ${response.start} ו-${response.end}.</div>`;
                return;
            }
            let html = `<strong>נמצאו ${response.results.length} פסוקים (אות פותחת: ${response.start}, סוגרת: ${response.end}):</strong><br><br>`;
            response.results.forEach(item => {
                html += `<div class="card">
                            <div class="meta">תהילים פרק ${item.chapter}, פסוק ${item.verse}</div>
                            <div class="text">"${item.text}"</div>
                         </div>`;
            });
            area.innerHTML = html;
        });
    }
</script>
</body>
</html>
"""

import os  # ודאי שהשורה הזו מופיעה או תוסיפי אותה בראש הקובץ

if __name__ == '__main__':
    # השרת באינטרנט יקבע את הפורט באופן דינמי, ואם לא - ברירת המחדל תהיה 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)