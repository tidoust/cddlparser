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
    AMPERSAND = '&'

    # Identifiers + literals,
    IDENT = 'IDENT'
    COMMENT = 'COMMENT'
    STRING = 'STRING'
    NUMBER = 'NUMBER'
    FLOAT = 'FLOAT'
    CTLOP = 'CTLOP'
    BYTES = 'BYTES'

    # Operators,
    ASSIGN = '='
    ARROWMAP = '=>'
    TCHOICE = '/'
    GCHOICE = '//'
    TCHOICEALT = '/='
    GCHOICEALT = '//='
    PLUS = '+'
    MINUS = '-'
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
            case Tokens.COMMENT:
                output += self.literal
            case Tokens.STRING:
                output += '"' + self.literal + '"'
            case Tokens.NUMBER:
                output += self.literal
            case Tokens.FLOAT:
                output += self.literal
            case Tokens.CTLOP:
                output += '.' + self.literal
            case Tokens.BYTES:
                output += '\'' + self.literal + '\''
            case Tokens.EOF:
                pass
            case _:
                output += str(self.type)
        return output