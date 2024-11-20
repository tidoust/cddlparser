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