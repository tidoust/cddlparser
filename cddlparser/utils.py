from .tokens import Tokens


def isAlpha(ch: str) -> bool:
    return ("a" <= ch <= "z") or ("A" <= ch <= "Z")


def isExtendedAlpha(ch: str) -> bool:
    return isAlpha(ch) or ch in "@_$"


def isUint(literal: str) -> bool:
    return (
        len(literal) > 0
        and literal[0] in "123456789"
        and all(ch in "0123456789" for ch in literal)
    )
