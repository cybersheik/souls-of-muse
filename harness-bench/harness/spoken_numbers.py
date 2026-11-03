"""Cardinal spellings used by EN/VI speech instructions, without model calls.

This extracts explicit number forms, not intent. Human source review remains
necessary, especially for ambiguous Vietnamese words and ASR substitutions.
"""
import re

EN_ONES = "zero one two three four five six seven eight nine".split()
EN_TEENS = "ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
EN_TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
VI_ONES = "không một hai ba bốn năm sáu bảy tám chín".split()
VALUES = {word: n for n, word in enumerate(EN_ONES)}
VALUES.update({word: n + 10 for n, word in enumerate(EN_TEENS)})
VALUES.update({word: (n + 2) * 10 for n, word in enumerate(EN_TENS)})
VALUES.update({word: n for n, word in enumerate(VI_ONES)})
VALUES.update({"mốt": 1, "tư": 4, "lăm": 5, "mười": 10})


def choice(words):
    return "(?:" + "|".join(words) + ")"


en_unit = choice(EN_ONES[1:])
en_small = rf"(?:{choice(EN_TENS)}(?:[\s-]+{en_unit})?|{choice(EN_TEENS)}|{choice(EN_ONES)})"
en_chunk = rf"(?:{en_unit}\s+hundred(?:\s+(?:and\s+)?{en_small})?|{en_small})"
vi_unit = choice(VI_ONES + ["mốt", "tư", "lăm"])
vi_small = rf"(?:{choice(VI_ONES[2:])}\s+mươi(?:\s+{vi_unit})?|mười(?:\s+{vi_unit})?|{vi_unit})"
vi_chunk = rf"(?:{choice(VI_ONES)}\s+trăm(?:\s+(?:(?:lẻ|linh)\s+{vi_unit}|{vi_small}))?|{vi_small})"


def pattern(chunk, million, thousand, join=""):
    separator = r"(?:\s*,\s*|\s+)"
    tail = rf"(?:{separator}{join}{chunk})?"
    full = (rf"(?:{chunk}\s+{million}(?:{separator}{join}{chunk}\s+{thousand})?{tail}"
            rf"|{chunk}\s+{thousand}{tail}|{chunk})")
    # Do not consume the start of the next independently scaled number.
    return re.compile(rf"(?<!\w){full}(?!\w)(?!\s+(?:hundred|thousand|million|mươi|trăm|nghìn|ngàn|triệu)\b)")


PATTERNS = {"en": pattern(en_chunk, "million", "thousand", r"(?:and\s+)?"),
            "vi": pattern(vi_chunk, "triệu", "(?:nghìn|ngàn)", r"(?:(?:lẻ|linh)\s+)?")}


def value(phrase):
    total = part = 0
    for word in re.split(r"[\s,-]+", phrase):
        if word in ("and", "lẻ", "linh"):
            continue
        if word in ("hundred", "trăm"):
            part *= 100
        elif word == "mươi":
            part = part // 100 * 100 + part % 100 * 10
        elif word in ("thousand", "nghìn", "ngàn", "million", "triệu"):
            total += part * (1_000_000 if word in ("million", "triệu") else 1000)
            part = 0
        else:
            part += VALUES[word]
    return str(total + part)


def numeric_text(text, lang=None):
    for language in ((lang,) if lang in PATTERNS else ("en", "vi")):
        def replace(match):
            phrase = match.group()
            following = text[match.end():]
            if language == "vi" and phrase == "không":
                fraction = re.search(rf"phẩy(?:\s+{choice(VI_ONES)})*\s*$", text[:match.start()])
                quantity = re.match(r"\s+(?:phẩy|lần|nhịp|phách|giây|phút|bpm|nốt|dây|ô)\b", following)
                if not (fraction or quantity):
                    return phrase  # ordinary negation, not a cardinal zero
            if language == "vi" and ((phrase == "năm" and re.match(r"\s+(?:nay|ngoái|tới|sau|trước)\b", following))
                                      or (phrase == "ba" and re.match(r"\s+của\b", following))):
                return phrase
            return value(phrase)
        text = PATTERNS[language].sub(replace, text)
    # A spoken fraction may spell each digit separately: point zero five.
    return re.sub(r"\b(\d+)\s+(?:point|phẩy)\s+(\d+(?:\s+\d+)*)\b",
                  lambda m: m[1] + "." + "".join(m[2].split()), text)
