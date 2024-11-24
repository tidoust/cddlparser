from enum import StrEnum
from dataclasses import dataclass

class Tokens(StrEnum):
    ILLEGAL = 'ILLEGAL'
    EOF = 'EOF'
    NL = '\n'
    SPACE = ' '
    UNDERSCORE = '_'
    DOLLAR = '$'
    ATSIGN = '@'
    CARET = '^'
    HASH = '#'
    TILDE = '~'

    # Identifiers + literals,
    IDENT = 'IDENT'
    INT = 'INT'
    COMMENT = 'COMMENT'
    STRING = 'STRING'
    NUMBER = 'NUMBER'
    FLOAT = 'FLOAT'

    # Operators,
    ASSIGN = '='
    PLUS = '+'
    MINUS = '-'
    SLASH = '/'
    QUEST = '?'
    ASTERISK = '*'

    # Ranges,
    INCLRANGE = '..',
    EXCLRANGE = '...',

    # Delimiters,
    COMMA = ','
    DOT = '.'
    COLON = ':'
    SEMICOLON = ';'
    LPAREN = '('
    RPAREN = ')'
    LBRACE = '{'
    RBRACE = '}'
    LBRACK = '['
    RBRACK = ']'
    LT = '<'
    GT = '>'
    QUOT = '"'

@dataclass
class Token:
    type: Tokens
    literal: str
    whitespace: str = ''

    def str(self) -> str:
        output = self.whitespace
        match self.type:
            case Tokens.IDENT:
                output += self.literal
            case Tokens.INT:
                output += self.literal
            case Tokens.COMMENT:
                output += self.literal
            case Tokens.STRING:
                output += Tokens.QUOT + self.literal + Tokens.QUOT
            case Tokens.NUMBER:
                output += self.literal
            case Tokens.FLOAT:
                output += self.literal
            case Tokens.EOF:
                pass
            case _:
                output += str(self.type)
        return output