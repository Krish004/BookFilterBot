# plugins/query_utils.py
import re
from googletrans import Translator

translator = Translator()

# 🔹 Tamil check
def is_tamil(text: str) -> bool:
    return bool(re.search(r'[\u0B80-\u0BFF]', text))

# 🔹 Clean junk words
def clean_book_query(text: str) -> str:
    ENGLISH_JUNK = {"plz", "pls", "please", "bro", "send", "upload", "latest", "new", "give", "link", "file", "book", "books", "novel", "novels"}
    TAMIL_JUNK = {"கிடைக்குமா", "குடுங்க", "அனுப்புங்க", "வேணும்", "தருங்க", "புத்தகம்", "புத்தகங்கள்", "நாவல்", "நாவல்கள்", "எழுதிய"}

    words = re.split(r"[\s,.:;!?]+", text)  # split on space + punctuation
    filtered = [w for w in words if w and w.lower() not in ENGLISH_JUNK and w not in TAMIL_JUNK]

    query = " ".join(filtered)
    query = re.sub(r"[\u200b-\u200f]", "", query)  # zero width chars
    query = re.sub(r"\s+", " ", query).strip(" -_.,")
    return query.strip()

# 🔹 Main prepare function
def prepare_query(raw: str):
    """Extracts clean Tamil + English queries (handles author/title/mix)."""
    query = clean_book_query(raw)

    tamil_qs = []
    eng_qs = []

    # --- Handle `-` or `&` (split author vs title) ---
    parts = re.split(r"[-&]+", query)
    parts = [p.strip() for p in parts if p.strip()]

    # Add main query as well
    parts.append(query)

    for part in parts:
        if is_tamil(part):
            tamil_qs.append(part)
            try:
                eng_qs.append(translator.translate(part, src='ta', dest='en').text)
            except Exception:
                eng_qs.append(part)
        else:
            eng_qs.append(part)
            try:
                tamil_qs.append(translator.translate(part, src='en', dest='ta').text)
            except Exception:
                tamil_qs.append(part)

    # Deduplicate
    tamil_qs = list(dict.fromkeys([q.strip() for q in tamil_qs if q.strip()]))
    eng_qs = list(dict.fromkeys([q.strip() for q in eng_qs if q.strip()]))

    return tamil_qs, eng_qs
