"""
The scope and sequence for LexiLearn.

This is the order skills are taught in, loosely based on the Orton-Gillingham
sequence most structured literacy programmes use. It lives in code rather than
the database on purpose: the curriculum is versioned with the app, it's easy to
review in a pull request, and the tests can check every example word against
the decodability rules (tests/test_curriculum.py). If a content team ever needs
to edit it without a deploy, this is the module to move into the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from functools import cache


class Pattern(StrEnum):
    CLOSED = "closed"
    SUFFIX_S = "suffix_s"
    DIGRAPH = "digraph"
    WELDED = "welded"
    FLOSS = "floss"
    BLEND = "blend"
    TRIGRAPH = "trigraph"
    VCE = "vce"
    OPEN = "open"
    SILENT_E_OTHER = "silent_e_other"
    MULTISYLLABLE = "multisyllable"
    SUFFIX_ING = "suffix_ing"
    SUFFIX_ED = "suffix_ed"
    Y_AS_VOWEL = "y_as_vowel"
    CONTRACTION = "contraction"
    VOWEL_TEAM = "vowel_team"
    R_CONTROLLED = "r_controlled"
    CONSONANT_LE = "consonant_le"
    DIPHTHONG = "diphthong"
    SOFT_C_G = "soft_c_g"
    ADVANCED_SPELLING = "advanced_spelling"


PATTERN_LEVELS: dict[Pattern, int] = {
    Pattern.CLOSED: 1,
    Pattern.SUFFIX_S: 1,
    Pattern.DIGRAPH: 2,
    Pattern.WELDED: 2,
    Pattern.FLOSS: 2,
    Pattern.BLEND: 3,
    Pattern.TRIGRAPH: 3,
    Pattern.VCE: 4,
    Pattern.OPEN: 4,
    Pattern.SILENT_E_OTHER: 4,
    Pattern.MULTISYLLABLE: 5,
    Pattern.SUFFIX_ING: 5,
    Pattern.SUFFIX_ED: 5,
    Pattern.Y_AS_VOWEL: 5,
    Pattern.CONTRACTION: 5,
    Pattern.VOWEL_TEAM: 6,
    Pattern.R_CONTROLLED: 7,
    Pattern.CONSONANT_LE: 8,
    Pattern.DIPHTHONG: 8,
    Pattern.SOFT_C_G: 8,
    Pattern.ADVANCED_SPELLING: 8,
}

PATTERN_LABELS: dict[Pattern, str] = {
    Pattern.CLOSED: "Closed syllable (short vowel)",
    Pattern.SUFFIX_S: "Plural -s",
    Pattern.DIGRAPH: "Digraph (sh, ch, th, wh, ck, qu)",
    Pattern.WELDED: "Welded sound (ng, nk)",
    Pattern.FLOSS: "Double letters (ff, ll, ss, zz)",
    Pattern.BLEND: "Consonant blend",
    Pattern.TRIGRAPH: "tch or dge",
    Pattern.VCE: "Silent e (a-e, i-e, o-e, u-e)",
    Pattern.OPEN: "Open syllable (long vowel)",
    Pattern.SILENT_E_OTHER: "Other silent e",
    Pattern.MULTISYLLABLE: "More than one syllable",
    Pattern.SUFFIX_ING: "Suffix -ing",
    Pattern.SUFFIX_ED: "Suffix -ed",
    Pattern.Y_AS_VOWEL: "y as a vowel",
    Pattern.CONTRACTION: "Contraction",
    Pattern.VOWEL_TEAM: "Vowel team",
    Pattern.R_CONTROLLED: "R-controlled vowel",
    Pattern.CONSONANT_LE: "Consonant-le",
    Pattern.DIPHTHONG: "Diphthong (oi, oy, ou, au, aw)",
    Pattern.SOFT_C_G: "Soft c or g",
    Pattern.ADVANCED_SPELLING: "Advanced spelling (ph, kn, wr...)",
}

LEVEL_TITLES: dict[int, str] = {
    1: "Short vowels",
    2: "Digraphs and double letters",
    3: "Blends",
    4: "Silent e and open syllables",
    5: "Longer words and endings",
    6: "Vowel teams",
    7: "Bossy r",
    8: "Consonant-le and tricky sounds",
}
MAX_LEVEL = max(LEVEL_TITLES)

# High frequency words that learners are taught by heart before (or instead
# of) sounding them out. Keyed by the level they're introduced at.
HEART_WORDS: dict[int, frozenset[str]] = {
    1: frozenset(
        {
            "a",
            "i",
            "the",
            "to",
            "of",
            "is",
            "was",
            "said",
            "you",
            "he",
            "she",
            "we",
            "me",
            "be",
            "are",
            "do",
            "his",
            "has",
            "as",
            "and",
            "go",
            "no",
            "so",
            "put",
        }
    ),
    2: frozenset(
        {
            "they",
            "what",
            "who",
            "where",
            "there",
            "here",
            "one",
            "two",
            "my",
            "by",
            "your",
            "were",
            "come",
            "some",
            "does",
            "want",
            "look",
        }
    ),
    3: frozenset(
        {
            "their",
            "could",
            "would",
            "should",
            "from",
            "have",
            "give",
            "live",
            "love",
            "many",
            "any",
            "been",
            "four",
            "says",
            "into",
        }
    ),
    4: frozenset(
        {
            "other",
            "mother",
            "brother",
            "again",
            "people",
            "friend",
            "once",
            "done",
            "gone",
            "eye",
            "only",
            "water",
            "laugh",
        }
    ),
    5: frozenset(
        {
            "because",
            "through",
            "though",
            "thought",
            "enough",
            "after",
            "every",
            "very",
            "always",
            "about",
            "school",
            "great",
            "know",
        }
    ),
    6: frozenset({"different", "beautiful", "answer", "busy", "special", "sure"}),
    7: frozenset({"ocean", "women", "whose", "sugar", "together", "world"}),
    8: frozenset({"island", "machine", "minute", "favourite", "favorite", "touch"}),
}


@cache
def heart_word_level(word: str) -> int | None:
    for level in sorted(HEART_WORDS):
        if word in HEART_WORDS[level]:
            return level
    return None


@dataclass(frozen=True, slots=True)
class Skill:
    code: str
    level: int
    title: str
    focus: str
    words: tuple[str, ...]
    tip: str
    patterns: tuple[Pattern, ...] = field(default_factory=tuple)


SKILLS: tuple[Skill, ...] = (
    # Level 1
    Skill(
        "1.1",
        1,
        "Short a",
        "The letter a says /a/ as in apple.",
        ("cat", "map", "bag", "sad", "ham", "jam", "van", "rat"),
        "Say /a/ while you trace the letter a in the air.",
        (Pattern.CLOSED,),
    ),
    Skill(
        "1.2",
        1,
        "Short i",
        "The letter i says /i/ as in itch.",
        ("sit", "pin", "dig", "hit", "lip", "big", "fin", "kid"),
        "Scratch your arm and say /i/ like 'itch'.",
        (Pattern.CLOSED,),
    ),
    Skill(
        "1.3",
        1,
        "Short o",
        "The letter o says /o/ as in octopus.",
        ("hot", "dog", "mop", "log", "top", "fox", "pot", "rod"),
        "Make your mouth round like an o and say /o/.",
        (Pattern.CLOSED,),
    ),
    Skill(
        "1.4",
        1,
        "Short u",
        "The letter u says /u/ as in up.",
        ("sun", "cup", "bug", "rug", "hut", "mud", "bus", "nut"),
        "Point up and say /u/.",
        (Pattern.CLOSED,),
    ),
    Skill(
        "1.5",
        1,
        "Short e",
        "The letter e says /e/ as in egg.",
        ("bed", "pet", "hen", "red", "leg", "ten", "web", "jet"),
        "Short e and short i sound close. Feel your jaw drop a little for /e/.",
        (Pattern.CLOSED,),
    ),
    Skill(
        "1.6",
        1,
        "Mixed short vowels and -s",
        "Read CVC words with every short vowel, and add -s.",
        ("cats", "pigs", "maps", "dogs", "beds", "cups", "hats", "pens"),
        "Tap one finger for each sound, then sweep to blend.",
        (Pattern.CLOSED, Pattern.SUFFIX_S),
    ),
    # Level 2
    Skill(
        "2.1",
        2,
        "sh, ch, th",
        "Two letters, one sound.",
        ("ship", "chop", "thin", "fish", "much", "bath", "shed", "chin"),
        "Hold up two fingers together: two letters make one sound.",
        (Pattern.DIGRAPH,),
    ),
    Skill(
        "2.2",
        2,
        "wh, ck, qu",
        "More letter pairs that make one sound.",
        ("when", "duck", "quit", "back", "quiz", "sock", "whip", "neck"),
        "ck comes right after a short vowel at the end of a word.",
        (Pattern.DIGRAPH,),
    ),
    Skill(
        "2.3",
        2,
        "Double ff, ll, ss, zz",
        "After a short vowel at the end of a word, f, l, s and z double.",
        ("bell", "puff", "miss", "buzz", "hill", "off", "fuzz", "less"),
        "Remember the floss rule: floss has a double s!",
        (Pattern.FLOSS,),
    ),
    Skill(
        "2.4",
        2,
        "ng and nk",
        "These sounds are glued together.",
        ("ring", "sang", "bank", "pink", "song", "sunk", "wing", "honk"),
        "Keep ng and nk together like they're glued.",
        (Pattern.WELDED,),
    ),
    # Level 3
    Skill(
        "3.1",
        3,
        "Starting blends",
        "Two consonants at the start, both sounds heard.",
        ("stop", "frog", "clap", "swim", "drip", "plan", "slip", "grab"),
        "Say each sound slowly, then faster until they blend.",
        (Pattern.BLEND,),
    ),
    Skill(
        "3.2",
        3,
        "Ending blends",
        "Two consonants at the end, both sounds heard.",
        ("hand", "lamp", "best", "milk", "tent", "jump", "sand", "gift"),
        "Don't drop the last sound. Tap it on the table.",
        (Pattern.BLEND,),
    ),
    Skill(
        "3.3",
        3,
        "tch and dge",
        "After a short vowel, /ch/ is often tch and /j/ is often dge.",
        ("match", "catch", "badge", "fudge", "ditch", "hedge", "pitch", "ledge"),
        "The t and d are bodyguards that protect the short vowel.",
        (Pattern.TRIGRAPH,),
    ),
    # Level 4
    Skill(
        "4.1",
        4,
        "a-e and i-e",
        "Silent e makes the vowel say its name.",
        ("cake", "bike", "lake", "time", "game", "kite", "made", "ride"),
        "Draw an arrow from the e back to the vowel: it jumps over one letter.",
        (Pattern.VCE,),
    ),
    Skill(
        "4.2",
        4,
        "o-e, u-e, e-e",
        "Silent e works with every vowel.",
        ("home", "cute", "rope", "mule", "hope", "bone", "theme", "note"),
        "Read it without the e first, then add the e and hear it change.",
        (Pattern.VCE,),
    ),
    Skill(
        "4.3",
        4,
        "Open syllables",
        "When a vowel is at the end, it says its name.",
        ("go", "me", "hi", "she", "no", "we", "so", "be"),
        "Open your hand like an open door: nothing stops the vowel.",
        (Pattern.OPEN,),
    ),
    # Level 5
    Skill(
        "5.1",
        5,
        "Two closed syllables",
        "Split between the two consonants.",
        ("rabbit", "napkin", "sunset", "picnic", "muffin", "kitten", "basket", "insect"),
        "Find the vowels first, then split between the consonants.",
        (Pattern.MULTISYLLABLE,),
    ),
    Skill(
        "5.2",
        5,
        "Open first syllable",
        "One consonant in the middle usually goes with the second syllable.",
        ("robot", "music", "pilot", "open", "silent", "bacon", "student", "zero"),
        "Try the long vowel first. If it isn't a real word, try short.",
        (Pattern.MULTISYLLABLE, Pattern.OPEN),
    ),
    Skill(
        "5.3",
        5,
        "-ing and -ed",
        "Endings can be their own syllable.",
        ("jumping", "helped", "landed", "running", "hopping", "wished", "melted", "sitting"),
        "Cover the ending with your finger, read the base word, then add it back.",
        (Pattern.SUFFIX_ING, Pattern.SUFFIX_ED),
    ),
    Skill(
        "5.4",
        5,
        "y as a vowel",
        "At the end, y says /i/ in short words and /ee/ in longer ones.",
        ("my", "fly", "happy", "puppy", "sunny", "cry", "funny", "windy"),
        "Count the syllables: one syllable, y says /i/. Two, it says /ee/.",
        (Pattern.Y_AS_VOWEL,),
    ),
    # Level 6
    Skill(
        "6.1",
        6,
        "ai and ay",
        "Both say /ay/. ai is in the middle, ay is at the end.",
        ("rain", "play", "mail", "day", "train", "paint", "stay", "wait"),
        "ay likes to stay at the end of the word.",
        (Pattern.VOWEL_TEAM,),
    ),
    Skill(
        "6.2",
        6,
        "ee and ea",
        "Both usually say /ee/.",
        ("tree", "seed", "read", "team", "sheep", "beach", "meet", "leaf"),
        "When two vowels go walking, the first one usually does the talking.",
        (Pattern.VOWEL_TEAM,),
    ),
    Skill(
        "6.3",
        6,
        "oa, ow, oe",
        "These say /oh/.",
        ("boat", "snow", "toe", "road", "coat", "grow", "goat", "slow"),
        "Make a round mouth and hold the /oh/ sound.",
        (Pattern.VOWEL_TEAM,),
    ),
    Skill(
        "6.4",
        6,
        "igh and ie",
        "These say /eye/.",
        ("light", "night", "pie", "tie", "high", "bright", "lie", "fight"),
        "In igh, the g and h are silent.",
        (Pattern.VOWEL_TEAM,),
    ),
    Skill(
        "6.5",
        6,
        "oo, ew, ue",
        "These say /oo/.",
        ("moon", "food", "new", "blue", "spoon", "few", "true", "glue"),
        "Make a little circle with your lips and say /oo/.",
        (Pattern.VOWEL_TEAM,),
    ),
    # Level 7
    Skill(
        "7.1",
        7,
        "ar",
        "Bossy r changes the vowel: ar says /ar/.",
        ("car", "farm", "star", "park", "dark", "yard", "shark", "card"),
        "Open wide like at the doctor's and say 'ah', then add r.",
        (Pattern.R_CONTROLLED,),
    ),
    Skill(
        "7.2",
        7,
        "or",
        "or says /or/ as in fork.",
        ("fork", "corn", "storm", "horn", "sport", "short", "born", "torch"),
        "Picture a fork when you see or.",
        (Pattern.R_CONTROLLED,),
    ),
    Skill(
        "7.3",
        7,
        "er, ir, ur",
        "Three spellings, one sound: /er/.",
        ("her", "bird", "turn", "fern", "girl", "burn", "shirt", "hurt"),
        "These three are the same sound, so spelling them takes practice.",
        (Pattern.R_CONTROLLED,),
    ),
    # Level 8
    Skill(
        "8.1",
        8,
        "Consonant-le",
        "The consonant before le joins it as the last syllable.",
        ("table", "little", "candle", "puzzle", "apple", "bubble", "simple", "turtle"),
        "Count back three letters from the end: that's your last syllable.",
        (Pattern.CONSONANT_LE,),
    ),
    Skill(
        "8.2",
        8,
        "oi and oy",
        "Both say /oy/. oi is in the middle, oy at the end.",
        ("coin", "boy", "oil", "toy", "join", "joy", "soil", "point"),
        "oy, like boy, sits at the end.",
        (Pattern.DIPHTHONG,),
    ),
    Skill(
        "8.3",
        8,
        "ou and ow",
        "Both can say /ow/ as in ouch.",
        ("out", "cow", "house", "town", "loud", "cloud", "mouth", "down"),
        "Pretend you stubbed your toe: /ow/!",
        (Pattern.DIPHTHONG,),
    ),
    Skill(
        "8.4",
        8,
        "au and aw",
        "Both say /aw/.",
        ("saw", "paw", "launch", "cause", "draw", "haul", "lawn", "yawn"),
        "Open your mouth wide like a yawn.",
        (Pattern.DIPHTHONG,),
    ),
    Skill(
        "8.5",
        8,
        "Soft c and g",
        "Before e, i or y, c says /s/ and g often says /j/.",
        ("city", "face", "page", "ice", "nice", "cent", "huge", "stage"),
        "Look at the letter after c or g before you say it.",
        (Pattern.SOFT_C_G,),
    ),
)

SKILLS_BY_CODE: dict[str, Skill] = {s.code: s for s in SKILLS}


def skill_index(code: str) -> int:
    return next(i for i, s in enumerate(SKILLS) if s.code == code)


def skills_for_level(level: int) -> list[Skill]:
    return [s for s in SKILLS if s.level == level]


# Short passages used by the reading room when the AI is unavailable or its
# text doesn't pass the decodability check. Each one is checked in the tests.
PASSAGES: dict[int, tuple[str, str]] = {
    1: ("Sam and the cat", "Sam has a cat. The cat is fat. The cat sat on a mat. Sam and the cat nap."),
    2: (
        "On the ship",
        "Beth and Chad sit on the deck of a ship. Chad has a net. He gets a fish. "
        'It is a big fish! Beth yells, "Ring the bell!" Chad rings the bell. Ding, ding!',
    ),
    3: (
        "A trip to the pond",
        "Fran and Glen went to the pond. Frogs swam in the mud. A duck sat on a stump. "
        "Glen held a stick, and Fran felt the wind. It was a fun trip.",
    ),
    4: (
        "Kate and the kite",
        "Kate has a kite. She takes it up the hill. The wind is strong, and the kite "
        'rides up, up, up. Mike runs to Kate. "Can I hold it?" he asks. Kate smiles '
        "and hands him the line.",
    ),
    5: (
        "Muffin the rabbit",
        "Zack has a pet rabbit named Muffin. Muffin is a happy rabbit. She likes jumping "
        "and hopping on the grass. At sunset, Zack picks up Muffin and gives the rabbit a "
        "hug. Then Muffin naps in a basket.",
    ),
    6: (
        "A rainy day",
        "It was a rainy day. Dean and his dad stayed inside to bake a cake. Dad read the "
        "steps, and Dean mixed the eggs. Soon the cake was in the oven. When it was done, "
        "they ate it with a cup of tea.",
    ),
    7: (
        "Carla's farm",
        "Carla works on a farm. Every morning she feeds the horses and the birds. Her dog, "
        "Spark, barks at the sheep and helps her herd them. In the barn, Carla stores corn "
        "for the winter.",
    ),
    8: (
        "The old coin",
        "Roy found an old coin in the soil near the castle. He cleaned it with a cloth and "
        "saw a face on one side. Was it a king or a queen? Roy could not wait to show his "
        "uncle. His uncle smiled and said it was very rare.",
    ),
}
