from .tokens import Tokens


def isLetter(ch: str) -> bool:
    return ("a" <= ch <= "z") or ("A" <= ch <= "Z")


def isAlphabeticCharacter(ch: str) -> bool:
    return isLetter(ch) or ch in {Tokens.ATSIGN, Tokens.UNDERSCORE, Tokens.DOLLAR}
