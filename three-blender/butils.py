
def safe_name(name: str):
    ACCENT_MAP = {
        "á": "a", "à": "a", "ã": "a", "â": "a", "ä": "ae", "å": "a",
        "č": "c", "ć": "c", 
        "é": "e", "è": "e", "ê": "e", "ë": "e", 
        "í": "i", "ì": "i", "î": "i", "ï": "i",
        "ñ": "n",
        "ó": "o", "ò": "o", "ô": "o", "ö": "oe", "õ": "o", "ø": "o",
        "ř": "r",
        "š": "s", "ß": "ss",
        "ú": "u", "ù": "u", "û": "u", "ü": "ue", "ũ": "u",
        "ý": "y", "ž": "z"
    }
    
    for accented, plain in ACCENT_MAP.items():
        name = name.replace(accented, plain)
        name = name.replace(accented.upper(), plain.upper())
    name = (
        name.replace(" ", "_")
            .replace("-", "_")
            .replace(".", "_")
    )
    return name