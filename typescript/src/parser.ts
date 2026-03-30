import { ParserError } from "./errors.ts";
import { Lexer } from "./lexer.ts";
import { Token, Tokens } from "./tokens.ts";
import { isUint } from "./utils.ts";
import {
  CDDLTree,
  CDDLNode,
  Rule,
  GroupEntry,
  Group,
  Map,
  Array,
  GroupChoice,
  Type,
  Typename,
  Value,
  Operator,
  Tag,
  Range,
  Memberkey,
  ChoiceFrom,
  Occurrence,
  GenericParameters,
  GenericArguments
} from "./ast.ts";
import type {
  Type1,
  Type2,
  PreludeType
} from "./ast.ts";

const NIL_TOKEN: Token = new Token(Tokens.ILLEGAL, "");

export class Parser {
  private lexer: Lexer;
  private curToken: Token = NIL_TOKEN;
  private peekToken: Token = NIL_TOKEN;

  private getCurToken(): Token {
    return this.curToken;
  }

  private getPeekToken(): Token {
    return this.peekToken;
  }

  constructor(source: string) {
    this.lexer = new Lexer(source);
    this._nextToken();
    this._nextToken();
  }

  public parse(): CDDLTree {
    const rules: Rule[] = [];

    while (this.getCurToken().type !== Tokens.EOF) {
      const rule = this._parseRule();
      rules.push(rule);
    }

    const tree = new CDDLTree(rules);
    tree.separator = this._nextToken();
    tree.setChildrenParent();

    this._convertGroupDefinitions(tree);

    return tree;
  }

  private _parseRule(): Rule {
    const typename = this._parseTypename(true, null);

    const assign = this._nextToken();
    let node: Rule;
    if (assign.type === Tokens.ASSIGN || assign.type === Tokens.GCHOICEALT) {
      const groupEntry = this._parseGroupEntry();
      node = new Rule(typename, assign, groupEntry);
    } else if (assign.type === Tokens.TCHOICEALT) {
      const ruleType = this._parseType();
      if (!(ruleType instanceof Type)) {
        throw new Error("Expected Type instance");
      }
      node = new Rule(typename, assign, ruleType);
    } else {
      throw this._parserError(
        `expected assignment (\`=\`, \`/=\`, \`//=\`) after \`${typename.serialize().trim()}\`, got \`${assign.serialize().trim()}\``
      );
    }
    return node;
  }

  private _parseGroupEntry(): GroupEntry {
    const occurrence = this._parseOccurrence();

    const looseType = this._parseType(true);
    let node: GroupEntry;
    if (looseType instanceof Memberkey) {
      const entryType = this._parseType(false);
      if (!(entryType instanceof Type)) {
        throw new Error("Expected Type instance");
      }
      node = new GroupEntry(occurrence, looseType, entryType);
    } else {
      node = new GroupEntry(occurrence, null, looseType);
    }
    return node;
  }

  private _parseType(loose: boolean = false): Type | Memberkey {
    const altTypes: Type1[] = [];
    let type1 = this._parseType1(loose);
    altTypes.push(type1);

    if (loose && this.getCurToken().type === Tokens.CARET) {
      const caretTokens: Token[] = [];
      caretTokens.push(this._nextToken());
      if (this.getCurToken().type !== Tokens.ARROWMAP) {
        throw this._parserError(
          `expected arrow map (\`=>\`), got \`#{(this.getCurToken().serialize() + this.getPeekToken().serialize()).trim()}\``
        );
      }
      caretTokens.push(this._nextToken());
      const key = new Memberkey(type1, true, false, caretTokens);
      return key;
    }
    if (loose && this.getCurToken().type === Tokens.ARROWMAP) {
      const key = new Memberkey(type1, false, false, [this._nextToken()]);
      return key;
    }
    if (loose && this.getCurToken().type === Tokens.COLON) {
      const key = new Memberkey(type1, true, true, [this._nextToken()]);
      return key;
    }

    while (this.getCurToken().type === Tokens.TCHOICE) {
      // Record the separator with the previous type
      type1.separator = this._nextToken();
      type1 = this._parseType1();
      altTypes.push(type1);
    }

    const node = new Type(altTypes);
    return node;
  }

  private _parseType1(loose: boolean = false): Type1 {
    const type2 = this._parseType2(loose);
    let node: Type1;
    if (this.getCurToken().type === Tokens.INCLRANGE || this.getCurToken().type === Tokens.EXCLRANGE) {
      const rangeop = this._nextToken();
      const maxType = this._parseType2();
      if (!(type2 instanceof Value || type2 instanceof Typename)) {
        throw this._parserError(
          `expected range min to be a value or a typename, got \`${type2.serialize().trim()}\``
        );
      }
      if (!(maxType instanceof Value || maxType instanceof Typename)) {
        throw this._parserError(
          `expected range max to be a value or a typename, got \`${maxType.serialize().trim()}\``
        );
      }
      node = new Range(type2, maxType, rangeop);
    } else if (this.getCurToken().type === Tokens.CTLOP) {
      // Note: validation of operator name could be added here
      const operator = this._nextToken();
      const controlType = this._parseType2();
      node = new Operator(type2, operator, controlType);
    } else {
      node = type2;
    }

    return node;
  }

  private _parseType2(loose: boolean = false): Type2 {
    let node: Type2;
    if (this.getCurToken().type === Tokens.LPAREN) {
      const openToken = this._nextToken();
      if (loose) {
        node = this._parseGroup(false);
      } else {
        const innerType = this._parseType();
        if (!(innerType instanceof Type)) {
          throw new Error("Expected Type instance");
        }
        node = innerType;
      }
      node.openToken = openToken;
      if (this.getCurToken().type !== Tokens.RPAREN) {
        throw this._parserError(
          `expected right parenthesis, got \`${this.getCurToken().serialize().trim()}\``
        );
      }
      node.closeToken = this._nextToken();
    } else if (this.getCurToken().type === Tokens.LBRACE) {
      const openToken = this._nextToken();
      node = this._parseGroup(true);
      node.openToken = openToken;
      if (this.getCurToken().type !== Tokens.RBRACE) {
        throw this._parserError(
          `expected right brace, got \`${this.getCurToken().serialize()}\``
        );
      }
      node.closeToken = this._nextToken();
    } else if (this.getCurToken().type === Tokens.LBRACK) {
      const openToken = this._nextToken();
      const group = this._parseGroup(false);
      node = new Array(group.groupChoices);
      node.openToken = openToken;
      if (this.getCurToken().type !== Tokens.RBRACK) {
        throw this._parserError(
          `expected right bracket, got \`${this.getCurToken().serialize().trim()}\``
        );
      }
      node.closeToken = this._nextToken();
    } else if (this.getCurToken().type === Tokens.TILDE) {
      const unwrapped = this._nextToken();
      node = this._parseTypename(false, unwrapped);
    } else if (this.getCurToken().type === Tokens.AMPERSAND) {
      const refToken = this._nextToken();
      if (this.getCurToken().type === Tokens.LPAREN) {
        const openToken = this._nextToken();
        const group = this._parseGroup(false);
        group.openToken = openToken;
        if (this.getCurToken().type !== Tokens.RPAREN) {
          throw this._parserError(
            `expected right parenthesis, got \`${this.getCurToken().serialize().trim()}\``
          );
        }
        group.closeToken = this._nextToken();
        node = new ChoiceFrom(group);
      } else {
        const typename = this._parseTypename(false, null);
        node = new ChoiceFrom(typename);
      }
      node.setComments(refToken);
    } else if (this.getCurToken().type === Tokens.HASH) {
      const hashToken = this._nextToken();
      if (
        (this.getCurToken().type === Tokens.NUMBER || this.getCurToken().type === Tokens.FLOAT) &&
        !this.getCurToken().startWithSpaces()
      ) {
        const number = this._nextToken();
        if (
          number.literal.length > 1 &&
          (number.literal[1] !== "." || number.literal.includes("e"))
        ) {
          throw this._parserError(
            `expected data item after "#" to match \`DIGIT ["." uint]\`, got \`${this.getCurToken().serialize().trim()}\``
          );
        }
        if (
          number.literal[0] === "6" &&
          this.getCurToken().type === Tokens.LPAREN &&
          !this.getCurToken().startWithSpaces()
        ) {
          const type2 = this._parseType2();
          if (!(type2 instanceof Type)) {
            throw new Error("Expected Type instance");
          }
          node = new Tag(number, type2);
        } else {
          node = new Tag(number);
        }
      } else {
        node = new Tag();
      }
      node.setComments(hashToken);
    } else if (this.getCurToken().type === Tokens.IDENT) {
      node = this._parseTypename(false, null);
    } else if (this.getCurToken().type === Tokens.STRING) {
      const value = this._nextToken();
      node = new Value(value.literal, "text");
      node.setComments(value);
    } else if (this.getCurToken().type === Tokens.BYTES) {
      const value = this._nextToken();
      node = new Value(value.literal, "bytes");
      node.setComments(value);
    } else if (this.getCurToken().type === Tokens.HEX) {
      const value = this._nextToken();
      node = new Value(value.literal, "hex");
      node.setComments(value);
    } else if (this.getCurToken().type === Tokens.BASE64) {
      const value = this._nextToken();
      node = new Value(value.literal, "base64");
      node.setComments(value);
    } else if (this.getCurToken().type === Tokens.NUMBER) {
      const value = this._nextToken();
      node = new Value(value.literal, "number");
      node.setComments(value);
    } else if (this.getCurToken().type === Tokens.FLOAT) {
      const value = this._nextToken();
      node = new Value(value.literal, "number");
      node.setComments(value);
    } else {
      throw this._parserError(
        `invalid type2 production, got \`${this.getCurToken().serialize().trim()}\``
      );
    }

    return node;
  }

  private _parseGroup(isMap: boolean = false): Group {
    const groupChoices: GroupChoice[] = [];
    while (true) {
      if (
        this.getCurToken().type === Tokens.RPAREN ||
        this.getCurToken().type === Tokens.RBRACE ||
        this.getCurToken().type === Tokens.RBRACK
      ) {
        break;
      }
      const groupEntries: GroupEntry[] = [];
      while (this.getCurToken().type !== Tokens.GCHOICE) {
        const groupEntry = this._parseGroupEntry();
        groupEntries.push(groupEntry);
        if (this.getCurToken().type === Tokens.COMMA) {
          groupEntry.separator = this._nextToken();
        }
        if (
          this.getCurToken().type === Tokens.RPAREN ||
          this.getCurToken().type === Tokens.RBRACE ||
          this.getCurToken().type === Tokens.RBRACK
        ) {
          break;
        }
      }
      const groupChoice = new GroupChoice(groupEntries);
      groupChoices.push(groupChoice);
      if (
        this.getCurToken().type === Tokens.RPAREN ||
        this.getCurToken().type === Tokens.RBRACE ||
        this.getCurToken().type === Tokens.RBRACK
      ) {
        break;
      }
      groupChoice.separator = this._nextToken();
    }

    let node: Map | Group;
    if (isMap) {
      node = new Map(groupChoices);
    } else {
      node = new Group(groupChoices);
    }
    return node;
  }

  private _parseOccurrence(): Occurrence | null {
    const tokens: Token[] = [];
    let occurrence: Occurrence | null = null;

    if (
      this.getCurToken().type === Tokens.QUEST ||
      this.getCurToken().type === Tokens.ASTERISK ||
      this.getCurToken().type === Tokens.PLUS
    ) {
      const n = this.getCurToken().type === Tokens.PLUS ? 1 : 0;
      let m = Infinity;

      if (
        this.getCurToken().type === Tokens.ASTERISK &&
        this.getPeekToken().type === Tokens.NUMBER &&
        isUint(this.getPeekToken().literal) &&
        !this.getPeekToken().startWithSpaces()
      ) {
        tokens.push(this._nextToken());
        m = parseInt(this.getCurToken().literal);
      }

      tokens.push(this._nextToken());
      occurrence = new Occurrence(n, m, tokens);
    } else if (
      this.getCurToken().type === Tokens.NUMBER &&
      isUint(this.getCurToken().literal) &&
      this.getPeekToken().type === Tokens.ASTERISK &&
      !this.getPeekToken().startWithSpaces()
    ) {
      const n = parseInt(this.getCurToken().literal);
      let m = Infinity;
      tokens.push(this._nextToken()); // eat "n"
      tokens.push(this._nextToken()); // eat "*"

      if (
        this.getCurToken().type === Tokens.NUMBER &&
        isUint(this.getCurToken().literal) &&
        !this.getCurToken().startWithSpaces()
      ) {
        m = parseInt(this.getCurToken().literal);
        tokens.push(this._nextToken());
      }

      occurrence = new Occurrence(n, m, tokens);
    }

    return occurrence;
  }

  private _parseTypename(definition: boolean = false, unwrapped: Token | null = null): Typename {
    if (this.getCurToken().type !== Tokens.IDENT) {
      throw this._parserError(
        `expected group identifier, got \`${this.getCurToken().serialize().trim()}\``
      );
    }
    const ident = this._nextToken();
    let parameters: GenericParameters | GenericArguments | null;
    if (definition) {
      parameters = this._parseGenericParameters();
    } else {
      parameters = this._parseGenericArguments();
    }
    const typename = new Typename(ident.literal, unwrapped, parameters);
    typename.setComments(ident);
    return typename;
  }

  private _parseGenericParameters(): GenericParameters | null {
    if (this.getCurToken().type !== Tokens.LT || this.getCurToken().startWithSpaces()) {
      return null;
    }
    const openToken = this._nextToken();

    const parameters: Typename[] = [];
    let name = this._parseTypename();
    parameters.push(name);
    while (this.getCurToken().type === Tokens.COMMA) {
      name.separator = this._nextToken();
      name = this._parseTypename();
      parameters.push(name);
    }

    const node = new GenericParameters(parameters);
    node.openToken = openToken;
    if (this.getCurToken().type !== Tokens.GT) {
      throw this._parserError(
        `expected \`>\` character to end generic production, got \`${this.getCurToken().serialize().trim()}\``
      );
    }
    node.closeToken = this._nextToken();
    return node;
  }

  private _parseGenericArguments(): GenericArguments | null {
    if (this.getCurToken().type !== Tokens.LT || this.getCurToken().startWithSpaces()) {
      return null;
    }
    const openToken = this._nextToken();

    const parameters: Type1[] = [];
    let type1 = this._parseType1();
    parameters.push(type1);
    while (this.getCurToken().type === Tokens.COMMA) {
      type1.separator = this._nextToken();
      type1 = this._parseType1();
      parameters.push(type1);
    }

    const node = new GenericArguments(parameters);
    node.openToken = openToken;
    if (this.getCurToken().type !== Tokens.GT) {
      throw this._parserError(
        `expected \`>\` character to end generic production, got \`${this.getCurToken().serialize().trim()}\``
      );
    }
    node.closeToken = this._nextToken();
    return node;
  }

  private _convertGroupDefinitions(tree: CDDLTree): void {
    const rulenames: Set<string> = new Set();
    const typenames: Set<string> = new Set();
    const groupnames: Set<string> = new Set();

    const checkUnderlyingType = (type1: Type1): string => {
      if (
        type1 instanceof Value ||
        type1 instanceof Map ||
        type1 instanceof Array ||
        type1 instanceof ChoiceFrom ||
        type1 instanceof Tag
      ) {
        return "type";
      }
      if (type1 instanceof Range) {
        return checkUnderlyingType(type1.min);
      }
      if (type1 instanceof Operator) {
        return checkUnderlyingType(type1.type);
      }
      if (type1 instanceof Typename) {
        const name = type1.name;
        if (typenames.has(name) || this._isPreludeType(name)) {
          return "type";
        }
        if (groupnames.has(name)) {
          return "group";
        }
      }
      return "unknown";
    };

    for (const rule of tree.rules) {
      rulenames.add(rule.name.name);

      if (typenames.size === 0) {
        typenames.add(rule.name.name);
      }

      if (rule.type instanceof Type) {
        typenames.add(rule.name.name);
        continue;
      }

      if (rule.assign.type === Tokens.TCHOICEALT) {
        typenames.add(rule.name.name);
      }

      if (rule.assign.type === Tokens.GCHOICEALT) {
        groupnames.add(rule.name.name);
      }

      if (rule.type.type.types.length > 1 && rule.type.type.openToken === null) {
        typenames.add(rule.name.name);
      }

      if (rule.type.occurrence !== null) {
        groupnames.add(rule.name.name);
      }
      if (rule.type.key !== null) {
        groupnames.add(rule.name.name);
      }
    }

    const lookForKeys = (node: CDDLNode): void => {
      if (
        node instanceof GroupEntry &&
        node.key !== null &&
        node.key.type instanceof Typename &&
        !node.key.hasColon &&
        rulenames.has(node.key.type.name)
      ) {
        typenames.add(node.key.type.name);
      }
      for (const child of node.getChildren()) {
        lookForKeys(child);
      }
    };

    lookForKeys(tree);

    let updateFound = true;
    while (updateFound) {
      updateFound = false;
      for (const rule of tree.rules) {
        if (rule.type instanceof Type) {
          for (const type1 of rule.type.types) {
            if (type1 instanceof Typename && rulenames.has(type1.name)) {
              if (!typenames.has(type1.name)) {
                updateFound = true;
                typenames.add(type1.name);
              }
            }
          }
          continue;
        }

        if (typenames.has(rule.name.name)) {
          for (const type1 of rule.type.type.types) {
            if (type1 instanceof Typename && rulenames.has(type1.name)) {
              if (!typenames.has(type1.name)) {
                updateFound = true;
                typenames.add(type1.name);
              }
            }
          }
        }
        if (groupnames.has(rule.name.name)) {
          for (const type1 of rule.type.type.types) {
            if (type1 instanceof Typename && rulenames.has(type1.name)) {
              if (!groupnames.has(type1.name)) {
                updateFound = true;
                groupnames.add(type1.name);
              }
            }
          }
        }
        if (rule.assign.type === Tokens.ASSIGN) {
          const defTypes: Set<string> = new Set(
            rule.type.type.types.map((type1) => checkUnderlyingType(type1))
          );
          if (defTypes.has("type") && defTypes.has("group")) {
            throw new ParserError(
              `CDDL semantic error - rule \`${rule.name.name}\` targets a mix of type and group rules`
            );
          }
          if (defTypes.has("type")) {
            if (!typenames.has(rule.name.name)) {
              updateFound = true;
              typenames.add(rule.name.name);
            }
          } else if (defTypes.has("group")) {
            if (!groupnames.has(rule.name.name)) {
              updateFound = true;
              groupnames.add(rule.name.name);
            }
          }
        }
      }
    }

    const overlap = [...typenames].filter((name) => groupnames.has(name));
    if (overlap.length > 0) {
      const overlapStr = overlap.join(", ");
      throw new ParserError(
        `CDDL semantic error - mix of type and group definitions for ${overlapStr}`
      );
    }

    for (const rule of tree.rules) {
      if (rule.type instanceof Type) {
        continue;
      }
      if (typenames.has(rule.name.name)) {
        if (!rule.type.isConvertibleToType()) {
          throw new ParserError(
            `CDDL semantic error - rule \`${rule.name.name}\` is a type definition but uses a group entry`
          );
        }
        rule.type = rule.type.type;
      }
    }
  }

  private _isPreludeType(name: string): boolean {
    const preludeTypes: PreludeType[] = [
      "any", "uint", "nint", "int", "bstr", "bytes", "tstr", "text", "tdate",
      "time", "number", "biguint", "bignint", "bigint", "integer", "unsigned",
      "decfrac", "bigfloat", "eb64url", "eb64legacy", "eb16", "encoded-cbor",
      "uri", "b64url", "b64legacy", "regexp", "mime-message", "cbor-any",
      "float16", "float32", "float64", "float16-32", "float32-64", "float",
      "false", "true", "bool", "nil", "null", "undefined"
    ];
    return (preludeTypes as string[]).includes(name);
  }

  private _nextToken(): Token {
    const curToken = this.curToken;
    this.curToken = this.peekToken;
    this.peekToken = this.lexer.nextToken();
    return curToken;
  }

  private _parserError(message: string): ParserError {
    const location = this.lexer.getLocation();
    return new ParserError(`CDDL syntax error - line ${location.line + 1}: ${message}`);
  }
}
