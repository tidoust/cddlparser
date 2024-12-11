import re
from .tokens import Tokens


def isAlpha(ch: str) -> bool:
    return ("a" <= ch <= "z") or ("A" <= ch <= "Z")


def isExtendedAlpha(ch: str) -> bool:
    return isAlpha(ch) or ch in "@_$"


def isUint(literal: str) -> bool:
    return re.match(r"^[1-9]\d*$", literal) is not None
