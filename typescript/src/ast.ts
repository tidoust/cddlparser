import { Token, Tokens } from "./tokens.ts";
import type { Serializable } from "./tokens.ts";

// Possible value types
export type ValueType = "number" | "text" | "bytes" | "hex" | "base64";

// Known control operators
export type OperatorName =
  | "and"
  | "bits"
  | "cbor"
  | "cborseq"
  | "default"
  | "eq"
  | "ge"
  | "gt"
  | "le"
  | "lt"
  | "ne"
  | "regexp"
  | "size"
  | "within"
  | "plus"
  | "cat"
  | "det"
  | "abnf"
  | "abnfb"
  | "feature"
  | "pcre";

// Prelude types defined in RFC810
export type PreludeType =
  | "any"
  | "uint"
  | "nint"
  | "int"
  | "bstr"
  | "bytes"
  | "tstr"
  | "text"
  | "tdate"
  | "time"
  | "number"
  | "biguint"
  | "bignint"
  | "bigint"
  | "integer"
  | "unsigned"
  | "decfrac"
  | "bigfloat"
  | "eb64url"
  | "eb64legacy"
  | "eb16"
  | "encoded-cbor"
  | "uri"
  | "b64url"
  | "b64legacy"
  | "regexp"
  | "mime-message"
  | "cbor-any"
  | "float16"
  | "float32"
  | "float64"
  | "float16-32"
  | "float32-64"
  | "float"
  | "false"
  | "true"
  | "bool"
  | "nil"
  | "null"
  | "undefined";

export type Markup = [string | null, string | null];

export class Marker {
  /**
   * Serialize a Token.
   *
   * The function must handle whitespaces and comments that the Token
   * contains.
   */
  serializeToken(token: Token, node: CDDLNode): string {
    return token.serialize();
  }

  /**
   * Serialize a Value.
   */
  serializeValue(prefix: string, value: string, suffix: string, node: Value): string {
    return prefix + value + suffix;
  }

  /**
   * Serialize a typename or a groupname
   */
  serializeName(name: string, node: Typename): string {
    return name;
  }

  /**
   * Wrapping markup for a node as a whole if needed
   */
  markupFor(node: CDDLNode): Markup {
    return [null, null];
  }
}

/**
 * Abstract base class for all nodes in the abstract syntax tree.
 */
export abstract class CDDLNode {
  parentNode: CDDLNode | null = null;

  serialize(marker?: Marker): string {
    // Make sure that parentNode relationships are properly set
    this.setChildrenParent();
    if (marker) {
      const markup = marker.markupFor(this);
      let output = markup[0] !== null ? markup[0] : "";
      output += this._serialize(marker);
      output += markup[1] !== null ? markup[1] : "";
      return output;
    }
    return this._serialize();
  }

  setChildrenParent(): void {
    /**
     * Initialize the parentNode links from children nodes to this node
     * so that marker can access and adapt its behavior based on the
     * current context.
     */
    for (const child of this.getChildren()) {
      child.parentNode = this;
      child.setChildrenParent();
    }
  }

  getChildren(): CDDLNode[] {
    /**
     * Return the list of children nodes attached to this node
     */
    return [];
  }

  /**
   * Function must be implemented in all subclasses.
   */
  abstract _serialize(marker?: Marker): string;

  protected _serializeToken(token: Token | null | undefined, marker?: Marker): string {
    if (!token) {
      return "";
    }
    if (!marker) {
      return token.serialize();
    }
    return marker.serializeToken(token, this);
  }

  toString(indent: number = 0): string {
    return "  ".repeat(indent) + this.constructor.name;
  }

  toJSON(): Serializable {
    return {};
  }
}

/**
 * A wrapped node is a node optionally enclosed in an open and close token.
 */
export abstract class WrappedNode extends CDDLNode {
  openToken: Token | null = null;
  closeToken: Token | null = null;

  override serialize(marker?: Marker): string {
    let output = "";
    if (marker) {
      const markup = marker.markupFor(this);
      output += markup[0] !== null ? markup[0] : "";
    }
    output += this._serializeToken(this.openToken, marker);
    output += this._serialize(marker);
    output += this._serializeToken(this.closeToken, marker);
    if (marker) {
      const markup = marker.markupFor(this);
      output += markup[1] !== null ? markup[1] : "";
    }
    return output;
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent)];
    if (this.openToken) {
      res.push(this.openToken.toString(indent + 1));
    }
    if (this.closeToken) {
      res.push(this.closeToken.toString(indent + 1));
    }
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      openToken: this.openToken?.toJSON(),
      closeToken: this.closeToken?.toJSON()
    });
  }
}

/**
 * A token node is a node that essentially represents a concrete token and/or
 * that may be part of a list.
 *
 * It stores the comments and whitespaces that may come *before* it, and an
 * optional separator token that may be used *after* it to separate it from
 * the next token in an underlying list.
 *
 * The separator remains null when the node is not part of a list, or not part
 * of a list that uses separators.
 *
 * A token node is a wrapped node if its openToken and closeToken properties
 * are set.
 */
export abstract class TokenNode extends WrappedNode {
  // Comments and whitespace *before* the node
  comments: Token[] = [];
  whitespace: string = "";
  separator: Token | null = null;

  /**
   * Function may be useful in subclasses to output something
   * before the comments and whitespace associated with the
   * main token
   */
  protected _prestr(marker?: Marker): string {
    return "";
  }

  override serialize(marker?: Marker): string {
    let output = this._prestr(marker);
    for (const comment of this.comments) {
      output += this._serializeToken(comment, marker);
    }
    output += this.whitespace;
    output += super.serialize(marker);
    output += this._serializeToken(this.separator, marker);
    return output;
  }

  setComments(token: Token): void {
    this.comments = token.comments;
    this.whitespace = token.whitespace;
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent)];
    for (const comment of this.comments) {
      res.push(comment.toString(indent + 1));
    }
    if (this.whitespace !== "") {
      res.push("  ".repeat(indent + 1) + `whitespaces: ${this.whitespace.length}`);
    }
    if (this.separator) {
      res.push(this.separator.toString(indent + 1));
    }
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      comments: this.comments.map(c => c.toJSON()),
      whitespace: this.whitespace,
      separator: this.separator?.toJSON()
    });
  }
}

/**
 * Represents a set of CDDL rules
 */
export class CDDLTree extends TokenNode {
  constructor(public rules: Rule[]) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return this.rules;
  }

  _serialize(marker?: Marker): string {
    return this.rules.map((item) => item.serialize(marker)).join("");
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent)];
    for (const rule of this.rules) {
      res.push(rule.toString(indent + 1));
    }
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      rules: this.rules.map(r => r.toJSON())
    });
  }
}

/**
 * A group definition
 */
export class Rule extends CDDLNode {
  constructor(
    public name: Typename,
    public assign: Token,
    public type: Type | GroupEntry
  ) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return [this.name, this.type];
  }

  _serialize(marker?: Marker): string {
    let output = this.name.serialize(marker);
    output += this._serializeToken(this.assign, marker);
    output += this.type.serialize(marker);
    return output;
  }

  override toString(indent: number = 0): string {
    return [
      super.toString(indent),
      this.name.toString(indent + 1),
      this.assign.toString(indent + 1),
      this.type.toString(indent + 1),
    ].join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      name: this.name.toJSON(),
      assign: this.assign.toJSON(),
      type: this.type.toJSON()
    });
  }
}

/**
 * A group entry
 */
export class GroupEntry extends TokenNode {
  constructor(
    public occurrence: Occurrence | null,
    public key: Memberkey | null,
    public type: Type
  ) {
    super();
  }

  override getChildren(): CDDLNode[] {
    const children: CDDLNode[] = [];
    if (this.occurrence) {
      children.push(this.occurrence);
    }
    if (this.key) {
      children.push(this.key);
    }
    children.push(this.type);
    return children;
  }

  _serialize(marker?: Marker): string {
    let output = "";
    if (this.occurrence) {
      output += this.occurrence.serialize(marker);
    }
    if (this.key) {
      output += this.key.serialize(marker);
    }
    output += this.type.serialize(marker);
    return output;
  }

  /**
   * Return true if GroupEntry can be converted to a proper Type.
   */
  isConvertibleToType(): boolean {
    return (
      this.occurrence === null &&
      this.key === null &&
      (!(this.type instanceof Group) ||
        this.type instanceof Array ||
        this.type instanceof Map)
    );
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent)];
    if (this.occurrence) {
      res.push(this.occurrence.toString(indent + 1));
    }
    if (this.key) {
      res.push(this.key.toString(indent + 1));
    }
    res.push(this.type.toString(indent + 1));
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      occurrence: this.occurrence?.toJSON(),
      key: this.key?.toJSON(),
      type: this.type.toJSON()
    });
  }
}

/**
 * A group, meaning a list of group choices wrapped in parentheses
 */
export class Group extends TokenNode {
  constructor(public groupChoices: GroupChoice[]) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return this.groupChoices;
  }

  _serialize(marker?: Marker): string {
    return this.groupChoices.map((item) => item.serialize(marker)).join("");
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent)];
    for (const item of this.groupChoices) {
      res.push(item.toString(indent + 1));
    }
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      groupChoices: this.groupChoices.map(g => g.toJSON())
    });
  }
}

/**
 * A map, meaning a list of group choices wrapped in curly braces
 */
export class Map extends Group {}

/**
 * An array
 */
export class Array extends Group {}

/**
 * A group choice
 */
export class GroupChoice extends TokenNode {
  constructor(public groupEntries: GroupEntry[]) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return this.groupEntries;
  }

  _serialize(marker?: Marker): string {
    return this.groupEntries.map((item) => item.serialize(marker)).join("");
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent)];
    for (const item of this.groupEntries) {
      res.push(item.toString(indent + 1));
    }
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      groupEntries: this.groupEntries.map(g => g.toJSON())
    });
  }
}

/**
 * A tag definition
 */
export class Tag extends TokenNode {
  constructor(
    public numericPart: Token | null = null,
    public typePart: Type | null = null
  ) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return this.typePart ? [this.typePart] : [];
  }

  _serialize(marker?: Marker): string {
    let output: string = this._serializeToken(new Token(Tokens.HASH, ""), marker);
    output += this._serializeToken(this.numericPart, marker);
    output += this.typePart ? this.typePart.serialize(marker) : "";
    return output;
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent) + " (#)"];
    if (this.numericPart) {
      res.push(this.numericPart.toString(indent + 1));
    }
    if (this.typePart) {
      res.push(this.typePart.toString(indent + 1));
    }
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      numericPart: this.numericPart?.toJSON(),
      typePart: this.typePart?.toJSON()
    });
  }
}

/**
 * Occurrence
 */
export class Occurrence extends TokenNode {
  constructor(
    public n: number,
    public m: number,
    public tokens: Token[] = []
  ) {
    super();
  }

  _serialize(marker?: Marker): string {
    return this.tokens.map((item) => this._serializeToken(item, marker)).join("");
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent)];
    for (const item of this.tokens) {
      res.push(item.toString(indent + 1));
    }
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      n: this.n,
      m: this.m,
      tokens: this.tokens.map(t => t.toJSON())
    });
  }
}

/**
 * A value (number, text or bytes)
 */
export class Value extends TokenNode {
  constructor(
    public value: string,
    public type: ValueType
  ) {
    super();
  }

  _serialize(marker?: Marker): string {
    let prefix: string = "";
    let suffix: string = "";
    if (this.type === "text") {
      prefix = '"';
      suffix = '"';
    } else if (this.type === "bytes") {
      prefix = "'";
      suffix = "'";
    } else if (this.type === "hex") {
      prefix = "h'";
      suffix = "'";
    } else if (this.type === "base64") {
      prefix = "b64'";
      suffix = "'";
    }
    if (!marker) {
      return prefix + this.value + suffix;
    }
    return marker.serializeValue(prefix, this.value, suffix, this);
  }

  override toString(indent: number = 0): string {
    return "  ".repeat(indent) + `${this.constructor.name} (${this.type}): ${this.value}`;
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      value: this.value,
      type: this.type
    });
  }
}

/**
 * A typename (or groupname)
 */
export class Typename extends TokenNode {
  constructor(
    public name: string,
    public unwrapped: Token | null,
    public parameters: GenericParameters | GenericArguments | null = null
  ) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return this.parameters ? [this.parameters] : [];
  }

  protected override _prestr(marker?: Marker): string {
    return this._serializeToken(this.unwrapped, marker);
  }

  _serialize(marker?: Marker): string {
    let output = "";
    if (!marker) {
      output = this.name;
    } else {
      output += marker.serializeName(this.name, this);
    }
    if (this.parameters) {
      output += this.parameters.serialize(marker);
    }
    return output;
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent), "  ".repeat(indent + 1) + this.name];
    if (this.unwrapped) {
      res.push(this.unwrapped.toString(indent + 1));
    }
    if (this.parameters) {
      res.push(this.parameters.toString(indent + 1));
    }
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      name: this.name,
      unwrapped: this.unwrapped?.toJSON(),
      parameters: this.parameters?.toJSON()
    });
  }
}

/**
 * A choice built from a group (or a groupname)
 */
export class ChoiceFrom extends TokenNode {
  constructor(public target: Group | Typename) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return [this.target];
  }

  _serialize(marker?: Marker): string {
    let output: string = this._serializeToken(new Token(Tokens.AMPERSAND, ""), marker);
    output += this.target.serialize(marker);
    return output;
  }

  override toString(indent: number = 0): string {
    const res: string[] = [
      super.toString(indent) + " (&)",
      this.target.toString(indent + 1),
    ];
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      target: this.target.toJSON()
    });
  }
}

/**
 * A type2 production is one of a few possibilities
 */
export type Type2 = Value | Typename | Type | Group | Map | Array | ChoiceFrom | Tag;

/**
 * A Range is a specific kind of Type1.
 */
export class Range extends TokenNode {
  constructor(
    public min: Value | Typename,
    public max: Value | Typename,
    public rangeop: Token
  ) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return [this.min, this.max];
  }

  _serialize(marker?: Marker): string {
    let output = this.min.serialize(marker);
    output += this._serializeToken(this.rangeop, marker);
    output += this.max.serialize(marker);
    return output;
  }

  override toString(indent: number = 0): string {
    const res: string[] = [
      super.toString(indent),
      this.min.toString(indent + 1),
      this.rangeop.toString(indent + 1),
      this.max.toString(indent + 1),
    ];
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      min: this.min.toJSON(),
      max: this.max.toJSON(),
      rangeop: this.rangeop.toJSON()
    });
  }
}

/**
 * An operator is a specific type of Type1
 */
export class Operator extends TokenNode {
  constructor(
    public type: Type2,
    public name: Token,
    public controller: Type2
  ) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return [this.type, this.controller];
  }

  _serialize(marker?: Marker): string {
    let output = this.type.serialize(marker);
    output += this._serializeToken(this.name, marker);
    output += this.controller.serialize(marker);
    return output;
  }

  override toString(indent: number = 0): string {
    const res: string[] = [
      super.toString(indent),
      this.type.toString(indent + 1),
      this.name.toString(indent + 1),
      this.controller.toString(indent + 1),
    ];
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      type: this.type.toJSON(),
      name: this.name.toJSON(),
      controller: this.controller.toJSON()
    });
  }
}

/**
 * A Type1 production is either a Type2, a Range or an Operator
 */
export type Type1 = Type2 | Range | Operator;

/**
 * Memberkey
 */
export class Memberkey extends CDDLNode {
  constructor(
    public type: Type1,
    public hasCut: boolean,
    public hasColon: boolean,
    public tokens: Token[] = []
  ) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return [this.type];
  }

  _serialize(marker?: Marker): string {
    let output = this.type.serialize(marker);
    output += this.tokens.map((token) => this._serializeToken(token, marker)).join("");
    return output;
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent), this.type.toString(indent + 1)];
    for (const item of this.tokens) {
      res.push(item.toString(indent + 1));
    }
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      type: this.type.toJSON(),
      hasCut: this.hasCut,
      hasColon: this.hasColon,
      tokens: this.tokens.map(t => t.toJSON())
    });
  }
}

/**
 * A Type is a list of Type1, each representing a possible choice.
 */
export class Type extends TokenNode {
  constructor(public types: Type1[]) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return this.types;
  }

  _serialize(marker?: Marker): string {
    return this.types.map((item) => item.serialize(marker)).join("");
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent)];
    for (const item of this.types) {
      res.push(item.toString(indent + 1));
    }
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      types: this.types.map(t => t.toJSON())
    });
  }
}

/**
 * A set of generic parameters
 */
export class GenericParameters extends WrappedNode {
  constructor(public parameters: Typename[]) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return this.parameters;
  }

  _serialize(marker?: Marker): string {
    return this.parameters.map((item) => item.serialize(marker)).join("");
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent)];
    for (const item of this.parameters) {
      res.push(item.toString(indent + 1));
    }
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      parameters: this.parameters.map(p => p.toJSON())
    });
  }
}

/**
 * A set of generic arguments
 */
export class GenericArguments extends WrappedNode {
  constructor(public parameters: Type1[]) {
    super();
  }

  override getChildren(): CDDLNode[] {
    return this.parameters;
  }

  _serialize(marker?: Marker): string {
    return this.parameters.map((item) => item.serialize(marker)).join("");
  }

  override toString(indent: number = 0): string {
    const res: string[] = [super.toString(indent)];
    for (const item of this.parameters) {
      res.push(item.toString(indent + 1));
    }
    return res.join("\n");
  }

  override toJSON(): Serializable {
    return Object.assign(super.toJSON(), {
      parameters: this.parameters.map(p => p.toJSON())
    });
  }
}
