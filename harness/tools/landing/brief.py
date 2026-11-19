"""The request text of the landing page read with fixed rules (no model): which rooms, services and disciplines it names.

`interpret(text)` returns what the text says and nothing else: counts of rooms (`rooms`), the garden, the services asked (`services`), the disciplines
they imply (`disciplines`), the number of floors and `notes` (codes the page translates) for what was understood but the harness cannot do yet. A kind of room that is not named
is not invented here; the proposal of the house (`house.py`) adds the usual rooms of a dwelling and says so.

What this rule reader cannot do (it would need a language model): free descriptions without counts ("a family house"), sizes and positions ("a 6 m living
room to the south"), negations ("without a garden"), and requests in other languages than Spanish and English. The form stays editable for that.
"""
import re

NUMBERS = {"un": 1, "una": 1, "uno": 1, "one": 1, "a": 1, "an": 1, "dos": 2, "two": 2, "tres": 3, "three": 3, "cuatro": 4, "four": 4, "cinco": 5, "five": 5,
           "seis": 6, "six": 6, "siete": 7, "seven": 7, "ocho": 8, "eight": 8}
# kind of room -> words (es and en, accents folded: the text is folded the same way)
KINDS = {
    "bedroom": r"dormitorios?|habitaci(?:on|ones)|cuartos?|piezas?|bedrooms?",
    "bathroom": r"banos?|sanitarios?|bathrooms?|toilets?",
    "kitchen": r"cocinas?|kitchens?",
    "living": r"livings?|salas? de estar|estar|comedor(?:es)?|living ?rooms?|dining ?rooms?",
    "garage": r"cocheras?|garages?|garajes?",
    "laundry": r"lavaderos?|laundry|laundries",
    "garden": r"jardin(?:es)?|patios?|gardens?|yards?",
}
SERVICES = {
    "lighting": r"iluminaci(?:on|ones)|luminarias?|luces|luz|lighting|lights?",
    "receptacles": r"tomacorrientes?|tomas?|enchufes?|receptacles?|outlets?|sockets?",
}
# discipline -> words; `architectural` and `electrical` have a pipeline, the others are only recorded
DISCIPLINES = {
    "architectural": r"casa|vivienda|departamento|duplex|house|home|dwelling|apartment|planta|plano|arquitect",
    "electrical": r"electric|instalacion electrica|iluminaci|tomacorriente|enchufe|lighting|receptacle|outlet",
    "hvac": r"aire acondicionado|climatiza|calefaccion|hvac|air conditioning|heating",
    "piping": r"canerias|plomeria|gas natural|cloacas|sanitaria|plumbing|piping",
    "fire": r"incendio|matafuego|fire",
    "telecom": r"wifi|datos|telefon|cctv|camaras|telecom",
    "civil": r"estructura|fundacion|hormigon|structural|foundation|concrete",
}
FLOORS = r"(?:planta alta|segundo piso|dos plantas|2 plantas|dos pisos|2 pisos|two floors|two storeys|two stories|second floor|upper floor|two-story)"
NOTE_CODES = {"hvac": "no_hvac_engine"}      # the page translates them (es / en)


def fold(text):
    """Lower case without accents (`baño` -> `bano`)."""
    table = str.maketrans("áéíóúüñ", "aeiouun")
    return str(text or "").lower().translate(table)


def _count(text, words):
    """How many of a kind the text names: `4 habitaciones` -> 4, `una cocina` -> 1, `jardin` alone -> 1; 0 when it does not appear."""
    found = 0
    for m in re.finditer(rf"(?:(\d+|[a-z]+)\s+)?(?:{words})\b", text):
        word = m.group(1)
        n = int(word) if word and word.isdigit() else NUMBERS.get(word, 1)
        found = max(found, n) if found else n
    return found


def _named(text, table):
    return {k: n for k, words in table.items() if (n := _count(text, words))}


def _disciplines(text, named, services):
    """The disciplines the words name, plus architecture when rooms were named and electrical when a service was."""
    asked = {d for d, words in DISCIPLINES.items() if re.search(words, text)}
    asked |= {"architectural"} if named else set()
    asked |= {"electrical"} if services else set()
    return sorted(asked, key=list(DISCIPLINES).index)


def interpret(request):
    """What the request says: {rooms, services, disciplines, floors, notes}. Empty text gives empty results."""
    text = fold(request)
    named = _named(text, KINDS)
    services = {k: True for k, words in SERVICES.items() if re.search(words, text)}
    asked = _disciplines(text, named, services)
    floors = 2 if re.search(FLOORS, text) else 1
    notes = [NOTE_CODES[k] for k in (["hvac"] if "hvac" in asked else [])]
    return {"rooms": named, "services": services, "disciplines": asked, "floors": floors, "notes": notes}
