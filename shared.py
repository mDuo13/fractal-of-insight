import re

def slugify(s):
    unacceptable_chars = re.compile(r"[^A-Za-z0-9 -]+")
    whitespace_regex = re.compile(r"\s+")
    s = re.sub(unacceptable_chars, "", s)
    s = re.sub(whitespace_regex, "-", s)
    if not s:
        s = "_"
    return s.lower()
