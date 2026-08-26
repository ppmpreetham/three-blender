import keyword
import re

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
    "ý": "y", "ž": "z",
}

def _build_translation_table() -> dict:
    table = {}
    for source, target in ACCENT_MAP.items():
        table[ord(source)] = target
        upper = source.upper()
        if len(upper) == 1:
            table[ord(upper)] = target.upper()
    return table


_TRANSLATION_TABLE = _build_translation_table()


def transliterate(name: str) -> str:
    return name.translate(_TRANSLATION_TABLE)


class NameSanitizer:
    def __init__(self):
        self._identifiers_used = set()
        self._files_used = set()
        self._identifiers = {}
        self._file_names = {}

    def sanitize(self, name: str) -> str:
        if name not in self._identifiers:
            self._identifiers[name] = self._unique(self._to_identifier(name), self._identifiers_used)
        return self._identifiers[name]

    def file_name(self, name: str) -> str:
        if name not in self._file_names:
            self._file_names[name] = self._unique(self.sanitize(name).lower(), self._files_used)
        return self._file_names[name]

    @staticmethod
    def _to_identifier(name: str) -> str:
        base = re.sub(r"[^A-Za-z0-9_]", "_", transliterate(name))
        if not base or base[0].isdigit():
            base = "_" + base
        if keyword.iskeyword(base):
            base += "_"
        return base

    @staticmethod
    def _unique(base: str, used: set) -> str:
        candidate = base
        counter = 1
        while candidate in used:
            counter += 1
            candidate = f"{base}_{counter}"
        used.add(candidate)
        return candidate
