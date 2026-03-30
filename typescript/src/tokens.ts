export type Serializable = { [key: string]: any };

export enum Tokens {
  ILLEGAL = "ILLEGAL",
  EOF = "EOF",
  NL = "\n",
  SPACE = " ",
  UNDERSCORE = "_",
  DOLLAR = "$",
  ATSIGN = "@",
  CARET = "^",
  HASH = "#",
  TILDE = "~",
  AMPERSAND = "&",

    // Identifiers + literals,
  IDENT = "IDENT",
  COMMENT = "COMMENT",
  STRING = "STRING",
  NUMBER = "NUMBER",
  FLOAT = "FLOAT",
  CTLOP = "CTLOP",
  BYTES = "BYTES",
  HEX = "HEX",
  BASE64 = "BASE64",

    // Operators,
  ASSIGN = "=",
  ARROWMAP = "=>",
  TCHOICE = "/",
  GCHOICE = "//",
  TCHOICEALT = "/=",
  GCHOICEALT = "//=",
  PLUS = "+",
  MINUS = "-",
  QUEST = "?",
  ASTERISK = "*",

    // Ranges,
  INCLRANGE = "..",
  EXCLRANGE = "...",

    // Delimiters,
  COMMA = ",",
  DOT = ".",
  COLON = ":",
  SEMICOLON = ";",
  LPAREN = "(",
  RPAREN = ")",
  LBRACE = "{",
  RBRACE = "}",
  LBRACK = "[",
  RBRACK = "]",
  LT = "<",
  GT = ">",
  QUOT = '"',
}

const reverseTokens = Object.entries(Tokens).reduce((acc, [key, value]) => {
  acc[value] = key;
  return acc;
}, {} as { [key: string]: string });

export class Token {
  type: Tokens;
  literal: string;
  comments: Token[];
  whitespace: string;

  constructor(type: Tokens, literal: string, comments: Token[] = [], whitespace: string = "") {
    this.type = type;
    this.literal = literal;
    this.comments = comments;
    this.whitespace = whitespace;
  }

  serialize(): string {
    let output = "";
    for (const comment of this.comments) {
      output += comment.serialize();
    }
    output += this.whitespace;
    switch (this.type) {
    case Tokens.IDENT:
    case Tokens.COMMENT:
    case Tokens.NUMBER:
    case Tokens.FLOAT:
      output += this.literal;
      break;
    case Tokens.STRING:
      output += '"' + this.literal + '"';
      break;
    case Tokens.CTLOP:
      output += "." + this.literal;
      break;
    case Tokens.BYTES:
      output += "'" + this.literal + "'";
      break;
    case Tokens.HEX:
      output += "h'" + this.literal + "'";
      break;
    case Tokens.BASE64:
      output += "b64'" + this.literal + "'";
      break;
    case Tokens.EOF:
      break;
    default:
      output += this.type.valueOf();
    }
    return output;
  }

  startWithSpaces(): boolean {
    return this.whitespace !== "" || this.comments.length > 0;
  }

  toString(indent: number = 0): string {
    const indentStr = "  ".repeat(indent);
    const res: string[] = [
      `${indentStr}${this.constructor.name}: ${reverseTokens[this.type]} (${this.type})`
    ];
    if (this.whitespace !== "") {
      res.push("  ".repeat(indent + 1) + `whitespaces: ${this.whitespace.length}`);
    }
    if (this.literal !== "") {
      res.push("  ".repeat(indent + 1) + `literal: ${this.literal}`);
    }
    for (const comment of this.comments) {
      res.push(comment.toString(indent + 1));
    }
    return res.join("\n");
  }

  toJSON(): Serializable {
    return {
      type: this.type,
      literal: this.literal,
      comments: this.comments?.map(c => c.toJSON()),
      whitespace: this.whitespace
    };
  }
}