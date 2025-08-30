# plugins/query_utils.py
import re
from googletrans import Translator

translator = Translator()

def is_tamil(text: str) -> bool:
    """Check if text contains Tamil characters."""
    return bool(re.search(r'[\u0B80-\u0BFF]', text))

def clean_book_query(text: str) -> str:
    """Remove junk words in Tamil + English from query."""
    ENGLISH_JUNK = {"plz", "pls", "please", "bro", "send", "upload", "latest", "new", "give", "link", "file"}
    TAMIL_JUNK = {"கிடைக்குமா", "குடுங்க", "அனுப்புங்க", "வேணும்", "தருங்க"}

    words = text.split()
    filtered = [w for w in words if w.lower() not in ENGLISH_JUNK and w not in TAMIL_JUNK]

    query = " ".join(filtered)
    query = re.sub(r"[\u200b-\u200f]", "", query)  # remove zero width chars
    query = re.sub(r"\s+", " ", query).strip(" -_.,")
    return query.strip()

def prepare_query(raw: str):
    """Return both Tamil + English versions of query."""
    query = clean_book_query(raw)

    tamil_q = query
    eng_q = query

    # If text is English, try Tamil translate
    if not is_tamil(query):
        try:
            tamil_q = translator.translate(query, src='en', dest='ta').text
        except Exception:
            tamil_q = query  # fallback

    # If text is Tamil, try English translate (for English books)
    else:
        try:
            eng_q = translator.translate(query, src='ta', dest='en').text
        except Exception:
            eng_q = query  # fallback

    return tamil_q, eng_q
