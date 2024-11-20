from dataclasses import dataclass
from .tokens import Token, Tokens
from .constants import WHITESPACE_CHARACTERS
from .utils import isLetter, isDigit, isAlphabeticCharacter, hasSpecialNumberCharacter

@dataclass
class Location:
    line: int = -1
    position: int = -1

class Lexer:
    input: str
    position: int = 0
    readPosition: int = 0
    ch: int = 0

    def __init__(self, source: str) -> None:
        self.input = source
        self.readChar()
    
    def readChar(self) -> None:
        if self.readPosition >= len(self.input):
            self.ch = 0
        else:
            self.ch = ord(self.input[self.readPosition])
        self.position = self.readPosition
        self.readPosition += 1

    def getLocation(self) -> Location:
        position = self.position - 2
        sourceLines = self.input.split('\n')
        sourceLineLength = [len(l) for l in sourceLines]
        i = 0

        for line, lineLength in enumerate(sourceLineLength):
            i += lineLength + 1
            lineBegin = i - lineLength
            if i > position:
                lineBegin = i - lineLength
                return Location(line, position - lineBegin + 1)

        return Location(0, 0)

    def getLine(self, lineNumber: int) -> str:
        return self.input.split('\n')[lineNumber]

    def getLocationInfo(self) -> str:
        loc = self.getLocation()
        line = self.getLine(loc.line) if loc.line >= 0 else ''
        locationInfo = line + '\n'
        locationInfo += ' ' * (loc.position if loc.position >= 0 else 0) + '^\n'
        locationInfo += ' ' * (loc.position if loc.position >= 0 else 0) + '|\n'
        return locationInfo

    def nextToken(self) -> Token:
        whitespace = self._readWhitespace()
        token = Token(Tokens.ILLEGAL, '', whitespace)
        literal = chr(self.ch)
        match literal:
            case '=':
                token = Token(Tokens.ASSIGN, '', whitespace)
            case '(':
                token = Token(Tokens.LPAREN, '', whitespace)
            case ')':
                token = Token(Tokens.RPAREN, '', whitespace)
            case '{':
                token = Token(Tokens.LBRACE, '', whitespace)
            case '}':
                token = Token(Tokens.RBRACE, '', whitespace)
            case '[':
                token = Token(Tokens.LBRACK, '', whitespace)
            case ']':
                token = Token(Tokens.RBRACK, '', whitespace)
            case '<':
                token = Token(Tokens.LT, '', whitespace)
            case '>':
                token = Token(Tokens.GT, '', whitespace)
            case '+':
                token = Token(Tokens.PLUS, '', whitespace)
            case ',':
                token = Token(Tokens.COMMA, '', whitespace)
            case '.':
                token = Token(Tokens.DOT, '', whitespace)
            case ':':
                token = Token(Tokens.COLON, '', whitespace)
            case '?':
                token = Token(Tokens.QUEST, '', whitespace)
            case '/':
                token = Token(Tokens.SLASH, '', whitespace)
            case '*':
                token = Token(Tokens.ASTERISK, '', whitespace)
            case '^':
                token = Token(Tokens.CARET, '', whitespace)
            case '#':
                token = Token(Tokens.HASH, '', whitespace)
            case '~':
                token = Token(Tokens.TILDE, '', whitespace)
            case '"':
                token = Token(Tokens.STRING, self._readString(), whitespace)
            case ';':
                token = Token(Tokens.COMMENT, self._readComment(), whitespace)
            case _:
                if self.ch == 0:
                    token = Token(Tokens.EOF, '', whitespace)
                elif isAlphabeticCharacter(literal):
                    return Token(Tokens.IDENT, self._readIdentifier(), whitespace)
                elif (
                    # positive number
                    isDigit(literal) or
                    # negative number
                    ((literal == Tokens.MINUS) and isDigit(self.input[self.readPosition]))
                ):
                    numberOrFloat = self._readNumberOrFloat()
                    return Token(
                        Tokens.FLOAT if Tokens.DOT in numberOrFloat else Tokens.NUMBER,
                        numberOrFloat,
                        whitespace
                    )

        self.readChar()
        return token

    def _readIdentifier(self) -> str:
        position = self.position

        # an identifier can contain
        # see https://tools.ietf.org/html/draft-ietf-cbor-cddl-08#section-3.1
        while (
            # a letter (a-z, A-Z)
            isLetter(chr(self.ch)) or
            # a digit (0-9)
            isDigit(chr(self.ch)) or
            # and special characters (-, _, @, ., $)
            self.ch in [
                ord(Tokens.MINUS),
                ord(Tokens.UNDERSCORE),
                ord(Tokens.ATSIGN),
                ord(Tokens.DOT),
                ord(Tokens.DOLLAR)
            ]
        ):
            self.readChar()

        return self.input[position:self.position]

    def _readComment(self) -> str:
        position = self.position

        while (self.ch and chr(self.ch) != Tokens.NL):
            self.readChar()

        return self.input[position:self.position]

    def _readString(self) -> str:
        position = self.position

        self.readChar() # eat "
        while (self.ch and chr(self.ch) != Tokens.QUOT):
            self.readChar() # eat any character until "

        return self.input[position + 1:self.position]

    def _readNumberOrFloat(self) -> str:
        position = self.position
        foundSpecialCharacter = False

        # a number of float can contain
        while (
            # a number
            isDigit(chr(self.ch)) or
            # a special character, e.g. ".", "x" and "b"
            hasSpecialNumberCharacter(self.ch)
        ):
            # ensure we respect ranges, e.g. 0..10
            # so break after the second dot and adjust read position
            if hasSpecialNumberCharacter(self.ch) and foundSpecialCharacter:
                self.position -= 1
                self.readPosition -= 1
                break

            foundSpecialCharacter = hasSpecialNumberCharacter(self.ch)
            self.readChar() # eat any character until a non digit or a 2nd dot

        return self.input[position:self.position]

    def _readWhitespace(self) -> str:
        position = self.position

        while chr(self.ch) in WHITESPACE_CHARACTERS:
            self.readChar()

        return self.input[position:self.position]
