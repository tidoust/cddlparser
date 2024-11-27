from pprint import pprint
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

    def _peekAtNextChar(self) -> str:
        if self.readPosition >= len(self.input):
            return ''
        else:
            return self.input[self.readPosition]

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
        comments = self._readComments()
        whitespace = ''
        if len(comments) > 0 and comments[-1].literal == '':
            whitespace = comments[-1].whitespace
            comments.pop()
        token = Token(Tokens.ILLEGAL, '')
        literal = chr(self.ch)
        tokenRead = False
        match literal:
            case '=':
                if self._peekAtNextChar() == '>':
                    self.readChar()
                    token = Token(Tokens.ARROWMAP, '', comments, whitespace)
                else:
                    token = Token(Tokens.ASSIGN, '', comments, whitespace)
            case '(':
                token = Token(Tokens.LPAREN, '', comments, whitespace)
            case ')':
                token = Token(Tokens.RPAREN, '', comments, whitespace)
            case '{':
                token = Token(Tokens.LBRACE, '', comments, whitespace)
            case '}':
                token = Token(Tokens.RBRACE, '', comments, whitespace)
            case '[':
                token = Token(Tokens.LBRACK, '', comments, whitespace)
            case ']':
                token = Token(Tokens.RBRACK, '', comments, whitespace)
            case '<':
                token = Token(Tokens.LT, '', comments, whitespace)
            case '>':
                token = Token(Tokens.GT, '', comments, whitespace)
            case '+':
                token = Token(Tokens.PLUS, '', comments, whitespace)
            case ',':
                token = Token(Tokens.COMMA, '', comments, whitespace)
            case '.':
                if self._peekAtNextChar() == '.':
                    self.readChar()
                    token = Token(Tokens.INCLRANGE, '', comments, whitespace)
                    if self._peekAtNextChar() == '.':
                        self.readChar()
                        token = Token(Tokens.EXCLRANGE, '', comments, whitespace)
                elif isAlphabeticCharacter(self._peekAtNextChar()):
                    self.readChar()
                    token = Token(Tokens.CTLOP, self._readIdentifier(), comments, whitespace)
                    tokenRead = True
            case ':':
                token = Token(Tokens.COLON, '', comments, whitespace)
            case '?':
                token = Token(Tokens.QUEST, '', comments, whitespace)
            case '/':
                if self._peekAtNextChar() == '/':
                    self.readChar()
                    token = Token(Tokens.GCHOICE, '', comments, whitespace)
                    if self._peekAtNextChar() == '=':
                        self.readChar()
                        token = Token(Tokens.GCHOICEALT, '', comments, whitespace)
                elif self._peekAtNextChar() == '=':
                    self.readChar()
                    token = Token(Tokens.TCHOICEALT, '', comments, whitespace)
                else:
                    token = Token(Tokens.TCHOICE, '', comments, whitespace)
            case '*':
                token = Token(Tokens.ASTERISK, '', comments, whitespace)
            case '^':
                token = Token(Tokens.CARET, '', comments, whitespace)
            case '#':
                token = Token(Tokens.HASH, '', comments, whitespace)
            case '~':
                token = Token(Tokens.TILDE, '', comments, whitespace)
            case '"':
                token = Token(Tokens.STRING, self._readString(), comments, whitespace)
            case '\'':
                token = Token(Tokens.BYTES, self._readBytesString(), comments, whitespace)
            case ';':
                token = Token(Tokens.COMMENT, self._readComment(), comments, whitespace)
                tokenRead = True
            case '&':
                token = Token(Tokens.AMPERSAND, '', comments, whitespace)
            case _:
                if self.ch == 0:
                    token = Token(Tokens.EOF, '', comments, whitespace)
                elif isAlphabeticCharacter(literal):
                    if literal == 'b' and self._peekAtNextChar() == '6':
                        self.readChar()
                        self.readChar()
                        if chr(self.ch) == '4' and self._peekAtNextChar() == '\'':
                            self.readChar()
                            token = Token(Tokens.BASE64, self._readBytesString(), comments, whitespace)
                        else:
                            # Looked like a b64 byte string, but that's just a regular
                            # identifier in the end
                            token = Token(Tokens.IDENT, 'b6' + self._readIdentifier(), comments, whitespace)
                            tokenRead = True
                    elif literal == 'h' and self._peekAtNextChar() == '\'':
                        self.readChar()
                        token = Token(Tokens.HEX, self._readBytesString(), comments, whitespace)
                    else:
                        token = Token(Tokens.IDENT, self._readIdentifier(), comments, whitespace)
                        tokenRead = True
                elif (
                    # positive number
                    isDigit(literal) or
                    # negative number
                    ((literal == Tokens.MINUS) and isDigit(self.input[self.readPosition]))
                ):
                    numberOrFloat = self._readNumberOrFloat()
                    token = Token(
                        Tokens.FLOAT if '.' in numberOrFloat else Tokens.NUMBER,
                        numberOrFloat,
                        comments,
                        whitespace
                    )
                    tokenRead = True

        if not tokenRead:
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
            self.ch in [ord(c) for c in '-_@.$']
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

    def _readBytesString(self) -> str:
        position = self.position

        self.readChar() # eat '
        while (self.ch and chr(self.ch) != '\''):
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

    def _readComments(self) -> list[Token]:
        comments: list[Token] = []
        while True:
            whitespace = self._readWhitespace()
            if chr(self.ch) != ';':
                # Record final whitespaces as an empty comment
                if whitespace != '':
                    token = Token(Tokens.COMMENT, '', [], whitespace)
                    comments.append(token)
                break
            token = Token(Tokens.COMMENT, self._readComment(), [], whitespace)
            comments.append(token)
        return comments
