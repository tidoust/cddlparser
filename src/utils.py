from .tokens import Tokens, Token

def isLetter(ch: str) -> bool:
    return ('a' <= ch and ch <= 'z') or ('A' <= ch and ch <= 'Z')

def isAlphabeticCharacter(ch: str) -> bool:
    return isLetter(ch) or ch == Tokens.ATSIGN or ch == Tokens.UNDERSCORE or ch == Tokens.DOLLAR

def isDigit(ch: str) -> bool:
    return ch.isdigit()

def hasSpecialNumberCharacter(ch: int) -> bool:
    return (
        ch == ord(Tokens.MINUS) or
        ch == ord(Tokens.DOT) or
        ch == ord('x') or
        ch == ord('b')
    )
