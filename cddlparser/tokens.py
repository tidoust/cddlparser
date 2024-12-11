from enum import Enum
from dataclasses import dataclass, field


class Tokens(Enum):
    ILLEGAL = "ILLEGAL"
    EOF = "EOF"
    NL = "\n"
    SPACE = " "
    UNDERSCORE = "_"
    DOLLAR = "$"
    ATSIGN = "@"
    CARET = "^"
    HASH = "#"
    TILDE = "~"
    AMPERSAND = "&"

    # Identifiers + literals,
    IDENT = "IDENT"
    COMMENT = "COMMENT"
    STRING = "STRING"
    NUMBER = "NUMBER"
    FLOAT = "FLOAT"
    CTLOP = "CTLOP"
    BYTES = "BYTES"
    HEX = "HEX"
    BASE64 = "BASE64"

    # Operators,
    ASSIGN = "="
    ARROWMAP = "=>"
    TCHOICE = "/"
    GCHOICE = "//"
    TCHOICEALT = "/="
    GCHOICEALT = "//="
    PLUS = "+"
    MINUS = "-"
    QUEST = "?"
    ASTERISK = "*"

    # Ranges,
    INCLRANGE = ".."
    EXCLRANGE = "..."

    # Delimiters,
    COMMA = ","
    DOT = "."
    COLON = ":"
    SEMICOLON = ";"
    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    LBRACK = "["
    RBRACK = "]"
    LT = "<"
    GT = ">"
    QUOT = '"'


@dataclass
class Token:
    type: Tokens
    literal: str
    comments: list["Token"] = field(default_factory=list)
    whitespace: str = ""

    def serialize(self) -> str:
        output = ""
        for comment in self.comments:
            output += comment.serialize()
        output += self.whitespace
        if self.type == Tokens.IDENT:
            output += self.literal
        elif self.type == Tokens.COMMENT:
            output += self.literal
        elif self.type == Tokens.STRING:
            output += '"' + self.literal + '"'
        elif self.type == Tokens.NUMBER:
            output += self.literal
        elif self.type == Tokens.FLOAT:
            output += self.literal
        elif self.type == Tokens.CTLOP:
            output += "." + self.literal
        elif self.type == Tokens.BYTES:
            output += "'" + self.literal + "'"
        elif self.type == Tokens.HEX:
            output += "h'" + self.literal + "'"
        elif self.type == Tokens.BASE64:
            output += "b64'" + self.literal + "'"
        elif self.type == Tokens.EOF:
            pass
        else:
            output += str(self.type.value)
        return output

    def startWithSpaces(self) -> bool:
        return self.whitespace != "" or len(self.comments) > 0
