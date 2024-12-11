from dataclasses import dataclass
from .tokens import Token, Tokens
from .utils import isExtendedAlpha
from .errors import ParserError


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
            return ""
        return self.input[self.readPosition]

    def getLocation(self) -> Location:
        position = self.position - 2
        sourceLines = self.input.split("\n")
        sourceLineLength = [len(line) for line in sourceLines]
        i = 0

        for line, lineLength in enumerate(sourceLineLength):
            i += lineLength + 1
            lineBegin = i - lineLength
            if i > position:
                lineBegin = i - lineLength
                return Location(line, position - lineBegin + 1)

        return Location(0, 0)

    def getLine(self, lineNumber: int) -> str:
        return self.input.split("\n")[lineNumber]

    def getLocationInfo(self) -> str:
        loc = self.getLocation()
        line = self.getLine(loc.line) if loc.line >= 0 else ""
        locationInfo = line + "\n"
        locationInfo += " " * (loc.position if loc.position >= 0 else 0) + "^\n"
        locationInfo += " " * (loc.position if loc.position >= 0 else 0) + "|\n"
        return locationInfo

    def nextToken(self) -> Token:
        comments = self._readComments()
        whitespace = ""
        if len(comments) > 0 and comments[-1].literal == "":
            whitespace = comments[-1].whitespace
            comments.pop()
        token = Token(Tokens.ILLEGAL, "")
        literal = chr(self.ch)
        tokenRead = False
        if literal == "=":
            if self._peekAtNextChar() == ">":
                self.readChar()
                token = Token(Tokens.ARROWMAP, "", comments, whitespace)
            else:
                token = Token(Tokens.ASSIGN, "", comments, whitespace)
        elif literal == "(":
            token = Token(Tokens.LPAREN, "", comments, whitespace)
        elif literal == ")":
            token = Token(Tokens.RPAREN, "", comments, whitespace)
        elif literal == "{":
            token = Token(Tokens.LBRACE, "", comments, whitespace)
        elif literal == "}":
            token = Token(Tokens.RBRACE, "", comments, whitespace)
        elif literal == "[":
            token = Token(Tokens.LBRACK, "", comments, whitespace)
        elif literal == "]":
            token = Token(Tokens.RBRACK, "", comments, whitespace)
        elif literal == "<":
            token = Token(Tokens.LT, "", comments, whitespace)
        elif literal == ">":
            token = Token(Tokens.GT, "", comments, whitespace)
        elif literal == "+":
            token = Token(Tokens.PLUS, "", comments, whitespace)
        elif literal == ",":
            token = Token(Tokens.COMMA, "", comments, whitespace)
        elif literal == ".":
            if self._peekAtNextChar() == ".":
                self.readChar()
                token = Token(Tokens.INCLRANGE, "", comments, whitespace)
                if self._peekAtNextChar() == ".":
                    self.readChar()
                    token = Token(Tokens.EXCLRANGE, "", comments, whitespace)
            elif isExtendedAlpha(self._peekAtNextChar()):
                self.readChar()
                token = Token(
                    Tokens.CTLOP, self._readIdentifier(), comments, whitespace
                )
                tokenRead = True
        elif literal == ":":
            token = Token(Tokens.COLON, "", comments, whitespace)
        elif literal == "?":
            token = Token(Tokens.QUEST, "", comments, whitespace)
        elif literal == "/":
            if self._peekAtNextChar() == "/":
                self.readChar()
                token = Token(Tokens.GCHOICE, "", comments, whitespace)
                if self._peekAtNextChar() == "=":
                    self.readChar()
                    token = Token(Tokens.GCHOICEALT, "", comments, whitespace)
            elif self._peekAtNextChar() == "=":
                self.readChar()
                token = Token(Tokens.TCHOICEALT, "", comments, whitespace)
            else:
                token = Token(Tokens.TCHOICE, "", comments, whitespace)
        elif literal == "*":
            token = Token(Tokens.ASTERISK, "", comments, whitespace)
        elif literal == "^":
            token = Token(Tokens.CARET, "", comments, whitespace)
        elif literal == "#":
            token = Token(Tokens.HASH, "", comments, whitespace)
        elif literal == "~":
            token = Token(Tokens.TILDE, "", comments, whitespace)
        elif literal == '"':
            token = Token(Tokens.STRING, self._readString(), comments, whitespace)
        elif literal == "'":
            token = Token(Tokens.BYTES, self._readBytesString(), comments, whitespace)
        elif literal == ";":
            token = Token(Tokens.COMMENT, self._readComment(), comments, whitespace)
            tokenRead = True
        elif literal == "&":
            token = Token(Tokens.AMPERSAND, "", comments, whitespace)
        elif self.ch == 0:
            token = Token(Tokens.EOF, "", comments, whitespace)
        elif isExtendedAlpha(literal):
            if literal == "b" and self._peekAtNextChar() == "6":
                self.readChar()
                self.readChar()
                if chr(self.ch) == "4" and self._peekAtNextChar() == "'":
                    self.readChar()
                    token = Token(
                        Tokens.BASE64,
                        self._readBytesString(),
                        comments,
                        whitespace,
                    )
                else:
                    # Looked like a b64 byte string, but that's just a regular
                    # identifier in the end
                    token = Token(
                        Tokens.IDENT,
                        self._readIdentifier("b6"),
                        comments,
                        whitespace,
                    )
                    tokenRead = True
            elif literal == "h" and self._peekAtNextChar() == "'":
                self.readChar()
                token = Token(Tokens.HEX, self._readBytesString(), comments, whitespace)
            else:
                token = Token(
                    Tokens.IDENT, self._readIdentifier(), comments, whitespace
                )
                tokenRead = True
        elif literal.isdigit() or literal == "-":
            # Numbers start with a digit or a minus
            numberOrFloat = self._readNumberOrFloat()
            token = Token(
                Tokens.FLOAT if "." in numberOrFloat else Tokens.NUMBER,
                numberOrFloat,
                comments,
                whitespace,
            )
            tokenRead = True

        if not tokenRead:
            self.readChar()
        return token

    def _readIdentifier(self, start: str = "") -> str:
        position = self.position

        # see https://tools.ietf.org/html/draft-ietf-cbor-cddl-08#section-3.1
        if start == "" and not isExtendedAlpha(chr(self.ch)):
            raise self._tokenError("identifier expected, found nothing")
        while (
            isExtendedAlpha(chr(self.ch))
            or chr(self.ch).isdigit()
            or chr(self.ch) in "-."
        ):
            self.readChar()

        identifier = start + self.input[position : self.position]
        if identifier[-1] in "-.":
            raise self._tokenError(
                'identifier cannot end with "-" or ".", found "{identifier}"'
            )
        return identifier

    def _readComment(self) -> str:
        position = self.position

        while self.ch and chr(self.ch) != "\n":
            self.readChar()

        return self.input[position : self.position]

    def _readString(self) -> str:
        position = self.position

        assert chr(self.ch) == '"'
        self.readChar()  # eat "
        while chr(self.ch) != '"':
            if (
                0x20 <= self.ch <= 0x21
                or 0x23 <= self.ch <= 0x5B
                or 0x5D <= self.ch <= 0x7E
                or 0x80 <= self.ch <= 0x10FFFD
            ):
                self.readChar()
            elif chr(self.ch) == "\\":
                self.readChar()
                if 0x20 <= self.ch <= 0x7E or 0x80 <= self.ch <= 0x10FFFD:
                    self.readChar()
                else:
                    raise self._tokenError("invalid escape character in text string")
            elif self.ch == 0x0A:
                self.readChar()
            elif self.ch == 0x0D and ord(self._peekAtNextChar()) == 0x0A:
                self.readChar()
                self.readChar()
            else:
                raise self._tokenError("invalid text string")

        return self.input[position + 1 : self.position]

    def _readBytesString(self) -> str:
        position = self.position

        assert chr(self.ch) == "'"
        self.readChar()  # eat '
        while chr(self.ch) != "'":
            if (
                0x20 <= self.ch <= 0x26
                or 0x28 <= self.ch <= 0x5B
                or 0x5D <= self.ch <= 0x10FFFD
            ):
                self.readChar()
            elif chr(self.ch) == "\\":
                self.readChar()
                if 0x20 <= self.ch <= 0x7E or 0x80 <= self.ch <= 0x10FFFD:
                    self.readChar()
                else:
                    raise self._tokenError("invalid escape character in byte string")
            elif self.ch == 0x0A:
                self.readChar()
            elif self.ch == 0x0D and ord(self._peekAtNextChar()) == 0x0A:
                self.readChar()
                self.readChar()
            else:
                raise self._tokenError("invalid byte string")

        return self.input[position + 1 : self.position]

    def _readNumberOrFloat(self) -> str:
        position = self.position
        dotFound = False

        # Negative numbers start with a minus prefix
        if chr(self.ch) == "-":
            self.readChar()

        if chr(self.ch) == "0":
            # Numbers that start with zero can either be hex numbers, binary
            # numbers, the number zero or a float lower than 1
            self.readChar()
            if chr(self.ch) == "x":
                # Hex number
                self.readChar()
                if chr(self.ch) not in "0123456789ABCDEF":
                    raise self._tokenError("hex number detected but no hex digit found")
                while chr(self.ch) in "0123456789ABCDEF":
                    self.readChar()
                if chr(self.ch) == ".":
                    dotFound = True
                    if self._peekAtNextChar() == ".":
                        # Two continuous dots is a range operator,
                        # number stops before the first dot.
                        return self.input[position : self.position]
                    self.readChar()
                    while chr(self.ch) in "0123456789ABCDEF":
                        self.readChar()
                if dotFound and chr(self.ch) != "p":
                    raise self._tokenError(
                        "hex number with fraction detected but no exponent found"
                    )
                if chr(self.ch) == "p":
                    # Number contains an exponent
                    self.readChar()
                    if chr(self.ch) in "+-":
                        self.readChar()
                    if not chr(self.ch).isdigit():
                        raise self._tokenError(
                            "hex number with exponent detected but no digit found for exponent"
                        )
                    while chr(self.ch).isdigit():
                        self.readChar()
            elif chr(self.ch) == "b":
                # Binary number
                self.readChar()
                if chr(self.ch) not in "01":
                    raise self._tokenError(
                        "binary number detected but no binary digit found"
                    )
                while chr(self.ch) in "01":
                    self.readChar()
            elif chr(self.ch) == ".":
                if self._peekAtNextChar() == ".":
                    # Two continuous dots is a range operator,
                    # number stops before the first dot.
                    return self.input[position : self.position]
                self.readChar()
                if not chr(self.ch).isdigit():
                    raise self._tokenError(
                        "number with fraction detected but no digit found in fraction"
                    )
                while chr(self.ch).isdigit():
                    self.readChar()
                if chr(self.ch) == "e":
                    # Number contains an exponent
                    self.readChar()
                    if chr(self.ch) in "+-":
                        self.readChar()
                    if not chr(self.ch).isdigit():
                        raise self._tokenError(
                            "number with exponent detected but no digit found in exponent"
                        )
                    while chr(self.ch).isdigit():
                        self.readChar()
            else:
                # Number is zero, next character is for another production
                pass
        else:
            while chr(self.ch).isdigit():
                self.readChar()
            if chr(self.ch) == ".":
                if self._peekAtNextChar() == ".":
                    # Two continuous dots is a range operator,
                    # number stops before the first dot.
                    return self.input[position : self.position]
                self.readChar()
                if not chr(self.ch).isdigit():
                    raise self._tokenError(
                        "number with fraction detected but no digit found in fraction"
                    )
                while chr(self.ch).isdigit():
                    self.readChar()
            if chr(self.ch) == "e":
                # Number contains an exponent
                self.readChar()
                if chr(self.ch) in "+-":
                    self.readChar()
                if not chr(self.ch).isdigit():
                    raise self._tokenError(
                        "number with exponent detected but no digit found in exponent"
                    )
                while chr(self.ch).isdigit():
                    self.readChar()

        return self.input[position : self.position]

    def _readWhitespace(self) -> str:
        position = self.position

        while chr(self.ch) in " \t\n\r":
            self.readChar()

        return self.input[position : self.position]

    def _readComments(self) -> list[Token]:
        comments: list[Token] = []
        while True:
            whitespace = self._readWhitespace()
            if chr(self.ch) != ";":
                # Record final whitespaces as an empty comment
                if whitespace != "":
                    token = Token(Tokens.COMMENT, "", [], whitespace)
                    comments.append(token)
                break
            token = Token(Tokens.COMMENT, self._readComment(), [], whitespace)
            comments.append(token)
        return comments

    def _tokenError(self, message: str) -> ParserError:
        location = self.getLocation()
        locInfo = self.getLocationInfo()
        return ParserError(
            f"CDDL token error - line {location.line + 1}, col {location.position}: {message}\n\n{locInfo}"
        )
