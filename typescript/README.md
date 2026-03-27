# A CDDL parser in JavaScript

This package contains a JavaScript implementation of a **Concise data definition language (CDDL) ([RFC 8610](https://datatracker.ietf.org/doc/html/rfc8610)) parser**.

CDDL expresses Concise Binary Object Representation (CBOR) data structures ([RFC 7049](https://datatracker.ietf.org/doc/html/rfc7049)). Its main goal is to provide an easy and unambiguous way to express structures for protocol messages and data formats that use CBOR or JSON.

The parser is intended to be used in **spec authoring tools to add cross-referencing logic within CDDL blocks**. It produces an Abstract Syntax Tree (AST) that closely follows the [CDDL grammar](https://datatracker.ietf.org/doc/html/rfc8610#appendix-B). The AST preserves whitespaces and comments. This AST is great for validation and for producing *marked up serializations of CDDL notations*. It is likely less directly suitable for processing CDDL for other purpose, as it is overly verbose.

The parser validates the CDDL syntax against the CDDL grammar and throws errors when the syntax is invalid. It also validates that there are no obvious type/group inconsistencies. Further validation logic is up to consumers (see also [Known validations](#known-validations)).

## Usage

The parser is available as an npm package. To install:

```bash
npm install cddlparser
```

You should then be able to write code such as:

```js
import { parse } from 'cddlparser';

const ast = parse(`person = {
  identity,                         ; an identity
  employer: tstr,                   ; some employer
}`);

console.log('The abstract syntax tree:');
console.log(ast.toString());

console.log();
console.log('Re-serialization:');
console.log(ast.serialize());
```

To create markup during serialization, you need to pass an object that subclasses the `Marker` class (see inline notes for a bit of documentation).

```js
import { parse } from 'cddlparser';
import { CDDLNode, Marker, Rule } from 'cddlparser/ast.js';

class StrongNameMarker extends Marker {
  serializeName(name, node) {
    return '<b>' + name + '</b>';
  }

  markupFor(node) {
    if (node instanceof Rule) {
      return ['<div class="rule">', '</div>'];
    }
    return super.markupFor(node)
  }
}

const ast = parse(`person = {
 identity,
 employer: tstr,
}`);

console.log(ast.serialize(new StrongNameMarker()));
```

This should produce:

```html
<div class="rule"><b>person</b> = {
  <b>identity</b>,
  <b>employer</b>: <b>tstr</b>,
}</div>
```

The AST may also be directly serialized as JSON, e.g.:

```js
const ast = parse(`person = {
 identity,
 employer: tstr,
}`);

console.log(JSON.stringify(ast, null, 2));
```

## Development notes

The source code of the JavaScript version of the CDDL parser is maintained in a GitHub repository that also contains a version written in Python. Both implementations are aligned, evolve jointly, and share tests. Check [`tidoust/cddlparser`](https://github.com/tidoust/cddlparser) for details.

The source code of the JavaScript version is written using TypeScript. To compile the TypeScript code to JavaScript from a local clone of the repository, install dependencies from the `typescript` folder and run `tsc`:

```bash
cd typescript
npm ci
tsc
```

This should produce JavaScript code in a `dist` folder (under the `typescript` folder).

**Note:** You'll need to install [TypeScript](https://www.typescriptlang.org/docs/handbook/typescript-tooling-in-5-minutes.html) first if not already done!


### Command-line interface

Code features a small CLI that takes the path to a CDDL file as parameter:

```bash
node dist/cddlparser.js ../tests/__fixtures__/example.cddl
```

This should print a serialization of the [Abstract Syntax Tree](https://en.wikipedia.org/wiki/Abstract_syntax_tree) (AST) produced by the parser, followed by a serialization of the AST as JSON, followed by re-serialization of the AST as CDDL, which should match the original file.

### How to run tests

You may run tests from a local copy of the code:

```bash
npm test
```

Parser tests compare the AST produced by the parser with a serialized snapshot of the expected AST. If you make changes to the parser and need to refresh a snapshot, delete the corresponding `tests/__snapshots__/[test].snap` file and run tests again.

Parser tests also compare the result of serializing the AST with the initial input.

The test files are a combination of the test files used in the other CDDL parser projects mentioned:
- [Test files from cddl-rs](https://github.com/anweiss/cddl/tree/main/tests/fixtures/cddl).
- [Test files from cddl](https://github.com/christian-bromann/cddl/tree/main/tests/__fixtures__), with a couple of fixes.

## Known limitations

- Updates to the CDDL grammar defined in [RFC 9862](https://www.rfc-editor.org/rfc/rfc9682.html) are not supported.
- As said, the parser validates the CDDL syntax against the CDDL grammar, and validates that there are no obvious type/group inconsistencies. The parser does not validate the CDDL beyond that. For example, the parser does not choke if two rules have the same name but define different types.
- The only logic that exists in the AST for now is the serialization logic. There are no facilities to import CDDL modules, resolve references, inline groups, validate CBOR, etc.
- The parser does not fully understand when a rule defines a type and when it defines a group. It may represent the right hand side of a type definition as a `GroupEntry` node, instead of as a `Type` node.
- Overall, the AST is verbose and could be simplified.

## Acknowledgments

The JavaScript version of the parser is directly adapted from the Python version of the parser, written to add CDDL support in [Bikeshed](https://github.com/speced/bikeshed). The JavaScript version is meant to help achieve the same purpose in [ReSpec](https://github.com/speced/respec). Both parsers exist because the spec editing scenario requires an AST that allows re-serialization of the CDDL without changes, preserving whitespaces and comments in particular, and existing CDDL parsers were not directly suitable for this usage. The parsers still take inspiration from them:

- [`cddl`](https://github.com/christian-bromann/cddl): a JavaScript implementation of a CDDL parser for Node.js, released under an MIT license, written by @christian-bromann. `cddlparser` started as a direct port of the JavaScript code, and the lexer remains similar to the JavaScript one. Testing structures and main test files also come from `cddl`. The parser in `cddlparser` is completely different though, given the need to preserve the original formatting (including whitespaces and comments) to re-serialize the AST back into a string.
- [`cddl-rs`](https://github.com/anweiss/cddl): a Rust implementation of a CDDL parser, released under an MIT license, written by @anweiss, that features a CDDL validator. The parser in `cddlparser` follows a similar "close to the CDDL grammar" logic. The `cddlparser` test suite also contains test files from the `cddl-rs` project.
- [`cddlc`](https://github.com/cabo/cddlc): A set of CDDL utilities written in Ruby by @cabo, along with CDDL extracts from IETF RFCs. The `cddlparser` test suite makes sure that CDDL extracts in the `cddlc` repository can be parsed and serialized again.
