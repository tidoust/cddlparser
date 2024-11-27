from enum import StrEnum
from dataclasses import dataclass, field

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
    HEX = 'HEX'
    BASE64 = 'BASE64'

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
    comments: list['Token'] = field(default_factory=list)
    whitespace: str = ''

    def str(self) -> str:
        output = ''
        for comment in self.comments:
            output += comment.str()
        output += self.whitespace
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
            case Tokens.HEX:
                output += 'h\'' + self.literal + '\''
            case Tokens.BASE64:
                output += 'b64\'' + self.literal + '\''
            case Tokens.EOF:
                pass
            case _:
                output += str(self.type)
        return output