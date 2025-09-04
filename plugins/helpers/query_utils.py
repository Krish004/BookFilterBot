# plugins/query_utils.py
import re
from googletrans import Translator

translator = Translator()
_translate_cache = {}  # 🔹 cache dict

def is_tamil(text: str) -> bool:
    return bool(re.search(r'[\u0B80-\u0BFF]', text))

def clean_book_query(text: str) -> str:
    ENGLISH_JUNK = {"plz", "pls", "please", "bro", "send", "upload", "latest", "new", "give", "link", "file", "book", "books", "novel", "novels"}
    TAMIL_JUNK = {"கிடைக்குமா", "குடுங்க", "அனுப்புங்க", "வேணும்", "தருங்க", "புத்தகம்", "புத்தகங்கள்", "நாவல்", "நாவல்கள்", "எழுதிய"}

    words = re.split(r"[\s,.:;!?]+", text)
    filtered = [w for w in words if w and w.lower() not in ENGLISH_JUNK and w not in TAMIL_JUNK]

    query = " ".join(filtered)
    query = re.sub(r"[\u200b-\u200f]", "", query)  # zero width chars
    query = re.sub(r"\s+", " ", query).strip(" -_.,")
    return query.strip()

def translate_word(word: str, src: str, dest: str) -> str:
    """Cached translator"""
    key = (word, src, dest)
    if key in _translate_cache:
        return _translate_cache[key]
    try:
        translated = translator.translate(word, src=src, dest=dest).text
    except Exception:
        translated = word
    _translate_cache[key] = translated
    return translated

def prepare_query(raw: str, do_translate=False):
    """
    Extracts clean Tamil + English queries.
    If do_translate=True → try translation (slower).
    """
    query = clean_book_query(raw)
    tamil_qs, eng_qs = [], []

    parts = re.split(r"[-&]+", query)
    parts = [p.strip() for p in parts if p.strip()]
    parts.append(query)  # add main query too

    for part in parts:
        if is_tamil(part):
            tamil_qs.append(part)
            if do_translate:
                eng_qs.append(translate_word(part, src='ta', dest='en'))
        else:
            eng_qs.append(part)
            if do_translate:
                tamil_qs.append(translate_word(part, src='en', dest='ta'))

    # Deduplicate
    tamil_qs = list(dict.fromkeys([q.strip() for q in tamil_qs if q.strip()]))
    eng_qs = list(dict.fromkeys([q.strip() for q in eng_qs if q.strip()]))

    return tamil_qs, eng_qs
