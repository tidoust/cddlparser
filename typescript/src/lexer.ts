import { Token, Tokens } from "./tokens.ts";
import { isExtendedAlpha } from "./utils.ts";
import { ParserError } from "./errors.ts";

export class Location {
  constructor(
    public line: number = -1,
    public position: number = -1
  ) {}
}

export class Lexer {
  private input: string;
  private position: number = 0;
  private readPosition: number = 0;
  private ch: number = 0;

  constructor(source: string) {
    this.input = source;
    this.readChar();
  }

  private readChar(): void {
    if (this.readPosition >= this.input.length) {
      this.ch = 0;
    } else {
      this.ch = this.input.charCodeAt(this.readPosition);
    }
    this.position = this.readPosition;
    this.readPosition += 1;
  }

  private _peekAtNextChar(): string {
    if (this.readPosition >= this.input.length) {
      return "";
    }
    return this.input[this.readPosition]!;
  }

  public getLocation(): Location {
    const position = this.position - 2;
    const sourceLines = this.input.split("\n");
    let i = 0;
    for (let line = 0; line < sourceLines.length; line++) {
      const lineLength = sourceLines[line]!.length;
      i += lineLength + 1;
      if (i > position) {
        const lineBegin = i - lineLength;
        return new Location(line, position - lineBegin + 1);
      }
    }

    return new Location(0, 0);
  }

  public getLine(lineNumber: number): string {
    return this.input.split("\n")[lineNumber]!;
  }

  public getLocationInfo(): string {
    const loc = this.getLocation();
    const line = loc.line >= 0 ? this.getLine(loc.line) : "";
    let locationInfo = line + "\n";
    locationInfo += " ".repeat(loc.position >= 0 ? loc.position : 0) + "^\n";
    locationInfo += " ".repeat(loc.position >= 0 ? loc.position : 0) + "|\n";
    return locationInfo;
  }

  public nextToken(): Token {
    const comments = this._readComments();
    let whitespace = "";
    if (comments.length > 0 && comments[comments.length - 1]!.literal === "") {
      whitespace = comments[comments.length - 1]!.whitespace;
      comments.pop();
    }
    let token = new Token(Tokens.ILLEGAL, "");
    const literal = String.fromCharCode(this.ch);
    let tokenRead = false;

    if (literal === "=") {
      if (this._peekAtNextChar() === ">") {
        this.readChar();
        token = new Token(Tokens.ARROWMAP, "", comments, whitespace);
      } else {
        token = new Token(Tokens.ASSIGN, "", comments, whitespace);
      }
    } else if (literal === "(") {
      token = new Token(Tokens.LPAREN, "", comments, whitespace);
    } else if (literal === ")") {
      token = new Token(Tokens.RPAREN, "", comments, whitespace);
    } else if (literal === "{") {
      token = new Token(Tokens.LBRACE, "", comments, whitespace);
    } else if (literal === "}") {
      token = new Token(Tokens.RBRACE, "", comments, whitespace);
    } else if (literal === "[") {
      token = new Token(Tokens.LBRACK, "", comments, whitespace);
    } else if (literal === "]") {
      token = new Token(Tokens.RBRACK, "", comments, whitespace);
    } else if (literal === "<") {
      token = new Token(Tokens.LT, "", comments, whitespace);
    } else if (literal === ">") {
      token = new Token(Tokens.GT, "", comments, whitespace);
    } else if (literal === "+") {
      token = new Token(Tokens.PLUS, "", comments, whitespace);
    } else if (literal === ",") {
      token = new Token(Tokens.COMMA, "", comments, whitespace);
    } else if (literal === ".") {
      if (this._peekAtNextChar() === ".") {
        this.readChar();
        token = new Token(Tokens.INCLRANGE, "", comments, whitespace);
        if (this._peekAtNextChar() === ".") {
          this.readChar();
          token = new Token(Tokens.EXCLRANGE, "", comments, whitespace);
        }
      } else if (isExtendedAlpha(this._peekAtNextChar())) {
        this.readChar();
        token = new Token(
          Tokens.CTLOP,
          this._readIdentifier(),
          comments,
          whitespace
        );
        tokenRead = true;
      }
    } else if (literal === ":") {
      token = new Token(Tokens.COLON, "", comments, whitespace);
    } else if (literal === "?") {
      token = new Token(Tokens.QUEST, "", comments, whitespace);
    } else if (literal === "/") {
      if (this._peekAtNextChar() === "/") {
        this.readChar();
        token = new Token(Tokens.GCHOICE, "", comments, whitespace);
        if (this._peekAtNextChar() === "=") {
          this.readChar();
          token = new Token(Tokens.GCHOICEALT, "", comments, whitespace);
        }
      } else if (this._peekAtNextChar() === "=") {
        this.readChar();
        token = new Token(Tokens.TCHOICEALT, "", comments, whitespace);
      } else {
        token = new Token(Tokens.TCHOICE, "", comments, whitespace);
      }
    } else if (literal === "*") {
      token = new Token(Tokens.ASTERISK, "", comments, whitespace);
    } else if (literal === "^") {
      token = new Token(Tokens.CARET, "", comments, whitespace);
    } else if (literal === "#") {
      token = new Token(Tokens.HASH, "", comments, whitespace);
    } else if (literal === "~") {
      token = new Token(Tokens.TILDE, "", comments, whitespace);
    } else if (literal === '"') {
      token = new Token(Tokens.STRING, this._readString(), comments, whitespace);
    } else if (literal === "'") {
      token = new Token(Tokens.BYTES, this._readBytesString(), comments, whitespace);
    } else if (literal === ";") {
      token = new Token(Tokens.COMMENT, this._readComment(), comments, whitespace);
      tokenRead = true;
    } else if (literal === "&") {
      token = new Token(Tokens.AMPERSAND, "", comments, whitespace);
    } else if (this.ch === 0) {
      token = new Token(Tokens.EOF, "", comments, whitespace);
    } else if (isExtendedAlpha(literal)) {
      if (literal === "b" && this._peekAtNextChar() === "6") {
        this.readChar();
        this.readChar();
        if (String.fromCharCode(this.ch) === "4" && this._peekAtNextChar() === "'") {
          this.readChar();
          token = new Token(
            Tokens.BASE64,
            this._readBytesString(),
            comments,
            whitespace
          );
        } else {
          // Looked like a b64 byte string, but that's just a regular identifier
          token = new Token(
            Tokens.IDENT,
            this._readIdentifier("b6"),
            comments,
            whitespace
          );
          tokenRead = true;
        }
      } else if (literal === "h" && this._peekAtNextChar() === "'") {
        this.readChar();
        token = new Token(Tokens.HEX, this._readBytesString(), comments, whitespace);
      } else {
        token = new Token(
          Tokens.IDENT,
          this._readIdentifier(),
          comments,
          whitespace
        );
        tokenRead = true;
      }
    } else if (this._isDigit(literal) || literal === "-") {
      // Numbers start with a digit or a minus
      const numberOrFloat = this._readNumberOrFloat();
      token = new Token(
        numberOrFloat.includes(".") ? Tokens.FLOAT : Tokens.NUMBER,
        numberOrFloat,
        comments,
        whitespace
      );
      tokenRead = true;
    }

    if (!tokenRead) {
      this.readChar();
    }
    return token;
  }

  private _isDigit(char: string): boolean {
    return char >= "0" && char <= "9";
  }

  private _readIdentifier(start: string = ""): string {
    const position = this.position;

    if (start === "" && !isExtendedAlpha(String.fromCharCode(this.ch))) {
      throw this._tokenError("expected identifier, got nothing");
    }
    while (
      isExtendedAlpha(String.fromCharCode(this.ch)) ||
      this._isDigit(String.fromCharCode(this.ch)) ||
      "-. ".includes(String.fromCharCode(this.ch))
    ) {
      const ch = String.fromCharCode(this.ch);
      if (ch === " ") break; // Handle space which might be in the list
      if ("-.".includes(ch)) {
        // Continue but identifier cannot end with these
      }
      this.readChar();
    }

    const identifier = start + this.input.substring(position, this.position);
    if (identifier.endsWith("-") || identifier.endsWith(".")) {
      throw this._tokenError(
        `identifier cannot end with \`-\` or \`.\`, got \`${identifier}\``
      );
    }
    return identifier;
  }

  private _readComment(): string {
    const position = this.position;

    while (this.ch && String.fromCharCode(this.ch) !== "\n") {
      this.readChar();
    }

    return this.input.substring(position, this.position);
  }

  private _readString(): string {
    const position = this.position;

    // assert String.fromCharCode(this.ch) === '"'
    this.readChar(); // eat "
    while (String.fromCharCode(this.ch) !== '"') {
      if (
        (this.ch >= 0x20 && this.ch <= 0x21) ||
        (this.ch >= 0x23 && this.ch <= 0x5b) ||
        (this.ch >= 0x5d && this.ch <= 0x7e) ||
        (this.ch >= 0x80 && this.ch <= 0x10fffd)
      ) {
        this.readChar();
      } else if (String.fromCharCode(this.ch) === "\\") {
        this.readChar();
        if (
          (this.ch >= 0x20 && this.ch <= 0x7e) ||
          (this.ch >= 0x80 && this.ch <= 0x10fffd)
        ) {
          this.readChar();
        } else {
          throw this._tokenError(
            `invalid escape character in text string \`${this.input.substring(position + 1, this.position)}\``
          );
        }
      } else if (this.ch === 0x0a) {
        this.readChar();
      } else if (this.ch === 0x0d && this._peekAtNextChar().charCodeAt(0) === 0x0a) {
        this.readChar();
        this.readChar();
      } else {
        throw this._tokenError(
          `invalid text string \`${this.input.substring(position + 1, this.position)}\``
        );
      }
    }

    return this.input.substring(position + 1, this.position);
  }

  private _readBytesString(): string {
    const position = this.position;

    // assert String.fromCharCode(this.ch) === "'"
    this.readChar(); // eat '
    while (String.fromCharCode(this.ch) !== "'") {
      if (
        (this.ch >= 0x20 && this.ch <= 0x26) ||
        (this.ch >= 0x28 && this.ch <= 0x5b) ||
        (this.ch >= 0x5d && this.ch <= 0x10fffd)
      ) {
        this.readChar();
      } else if (String.fromCharCode(this.ch) === "\\") {
        this.readChar();
        if (
          (this.ch >= 0x20 && this.ch <= 0x7e) ||
          (this.ch >= 0x80 && this.ch <= 0x10fffd)
        ) {
          this.readChar();
        } else {
          throw this._tokenError(
            `invalid escape character in byte string \`${this.input.substring(position + 1, this.position)}\``
          );
        }
      } else if (this.ch === 0x0a) {
        this.readChar();
      } else if (this.ch === 0x0d && this._peekAtNextChar().charCodeAt(0) === 0x0a) {
        this.readChar();
        this.readChar();
      } else {
        throw this._tokenError(
          `invalid byte string \`${this.input.substring(position + 1, this.position)}\``
        );
      }
    }

    return this.input.substring(position + 1, this.position);
  }

  private _readNumberOrFloat(): string {
    const position = this.position;
    let dotFound = false;

    if (String.fromCharCode(this.ch) === "-") {
      this.readChar();
    }

    if (String.fromCharCode(this.ch) === "0") {
      this.readChar();
      if (String.fromCharCode(this.ch) === "x") {
        // Hex number
        this.readChar();
        if (!"0123456789ABCDEF".includes(String.fromCharCode(this.ch).toUpperCase())) {
          throw this._tokenError(
            `expected hex number to contain hex digits, got \`${this.input.substring(position, this.position)}\``
          );
        }
        while ("0123456789ABCDEF".includes(String.fromCharCode(this.ch).toUpperCase())) {
          this.readChar();
        }
        if (String.fromCharCode(this.ch) === ".") {
          dotFound = true;
          if (this._peekAtNextChar() === ".") {
            return this.input.substring(position, this.position);
          }
          this.readChar();
          while ("0123456789ABCDEF".includes(String.fromCharCode(this.ch).toUpperCase())) {
            this.readChar();
          }
        }
        if (dotFound && String.fromCharCode(this.ch) !== "p") {
          throw this._tokenError(
            `expected hex number with fraction to have an exponent, got \`${this.input.substring(position, this.position)}\``
          );
        }
        if (String.fromCharCode(this.ch) === "p") {
          this.readChar();
          if ("+-".includes(String.fromCharCode(this.ch))) {
            this.readChar();
          }
          if (!this._isDigit(String.fromCharCode(this.ch))) {
            throw this._tokenError(
              `expected hex number with exponent to have a digit in exponent, got \`${this.input.substring(position, this.position)}\``
            );
          }
          while (this._isDigit(String.fromCharCode(this.ch))) {
            this.readChar();
          }
        }
      } else if (String.fromCharCode(this.ch) === "b") {
        // Binary number
        this.readChar();
        if (!"01".includes(String.fromCharCode(this.ch))) {
          throw this._tokenError(
            `expected binary number to have binary digits, got \`${this.input.substring(position, this.position)}\``
          );
        }
        while ("01".includes(String.fromCharCode(this.ch))) {
          this.readChar();
        }
      } else if (String.fromCharCode(this.ch) === ".") {
        if (this._peekAtNextChar() === ".") {
          return this.input.substring(position, this.position);
        }
        this.readChar();
        if (!this._isDigit(String.fromCharCode(this.ch))) {
          throw this._tokenError(
            `expected number with fraction to have digits in fraction part, got \`${this.input.substring(position, this.position)}\``
          );
        }
        while (this._isDigit(String.fromCharCode(this.ch))) {
          this.readChar();
        }
        if (String.fromCharCode(this.ch) === "e") {
          this.readChar();
          if ("+-".includes(String.fromCharCode(this.ch))) {
            this.readChar();
          }
          if (!this._isDigit(String.fromCharCode(this.ch))) {
            throw this._tokenError(
              `expected number with exponent to have digits in exponent, got \`${this.input.substring(position, this.position)}\``
            );
          }
          while (this._isDigit(String.fromCharCode(this.ch))) {
            this.readChar();
          }
        }
      }
    } else {
      while (this._isDigit(String.fromCharCode(this.ch))) {
        this.readChar();
      }
      if (String.fromCharCode(this.ch) === ".") {
        if (this._peekAtNextChar() === ".") {
          return this.input.substring(position, this.position);
        }
        this.readChar();
        if (!this._isDigit(String.fromCharCode(this.ch))) {
          throw this._tokenError(
            `expected number with fraction to have digits in fraction part, got \`${this.input.substring(position, this.position)}\``
          );
        }
        while (this._isDigit(String.fromCharCode(this.ch))) {
          this.readChar();
        }
      }
      if (String.fromCharCode(this.ch) === "e") {
        this.readChar();
        if ("+-".includes(String.fromCharCode(this.ch))) {
          this.readChar();
        }
        if (!this._isDigit(String.fromCharCode(this.ch))) {
          throw this._tokenError(
            `expected number with exponent to have digits in exponent, got \`${this.input.substring(position, this.position)}\``
          );
        }
        while (this._isDigit(String.fromCharCode(this.ch))) {
          this.readChar();
        }
      }
    }

    return this.input.substring(position, this.position);
  }

  private _readWhitespace(): string {
    const position = this.position;

    while (" \t\n\r".includes(String.fromCharCode(this.ch))) {
      this.readChar();
    }

    return this.input.substring(position, this.position);
  }

  private _readComments(): Token[] {
    const comments: Token[] = [];
    while (true) {
      const whitespace = this._readWhitespace();
      if (String.fromCharCode(this.ch) !== ";") {
        if (whitespace !== "") {
          const token = new Token(Tokens.COMMENT, "", [], whitespace);
          comments.push(token);
        }
        break;
      }
      const token = new Token(Tokens.COMMENT, this._readComment(), [], whitespace);
      comments.push(token);
    }
    return comments;
  }

  private _tokenError(message: string): ParserError {
    const location = this.getLocation();
    return new ParserError(`CDDL token error - line ${location.line + 1}: ${message}`);
  }
}
