# A CDDL parser in Python

> Concise data definition language ([RFC 8610](https://datatracker.ietf.org/doc/html/rfc8610)) parser implementation in Python.

CDDL expresses Concise Binary Object Representation (CBOR) data structures ([RFC 7049](https://datatracker.ietf.org/doc/html/rfc7049)). Its main goal is to provide an easy and unambiguous way to express structures for protocol messages and data formats that use CBOR or JSON.

This Python implementation provides a CDDL parser suitable for producing marked up serializations of the CDDL. It is intended to be used in spec authoring tools to add cross-referencing logic within CDDL blocks that the specs may define.

__Note:__ This is __work in progress__. Feel free to have a look at the code and report problems, but you may not want to rely on the code in a production setting.

## How to install and use

Clone the repository:

```bash
git clone https//github.com/tidoust/cddlparser
```

Then run `cddlparser.py`, passing in the path to a CDDL file as parameter

```bash
python cddlparser.py tests/__fixtures__/example.cddl
```

Through your local copy, you may import

```python
from cddlparser import parse
from prettyprint import pprint
ast = parse('''
  person = {
      identity,                         ; an identity
      employer: tstr,                   ; some employer
  }''')
pprint(ast)
```

That should print a serialization of the [Abstract Syntax Tree](https://en.wikipedia.org/wiki/Abstract_syntax_tree) (AST) produced by the parser, followed by a re-serialization of the AST, which should match the original file.

## How to run tests

```bash
python tests.py
```

Parser tests compare the AST produced by the parser with a serialized snapshot of the expected AST. If you make changes to the parser and need to refresh a snapshot, delete the corresponding `tests/__snapshots__/[test].snap` file and run tests again.

Parser tests also compare the result of serializing the AST with the initial input.

The test files are a combination of the test files used in the other CDDL parser projects mentioned:
- [Test files from cddl-rs](https://github.com/anweiss/cddl/tree/main/tests/fixtures/cddl).
- [Test files from cddl](https://github.com/christian-bromann/cddl/tree/main/tests/__fixtures__), with a couple of fixes.

The code uses static types. To validate types, [install `mypy`](https://mypy.readthedocs.io/en/stable/getting_started.html#installing-and-running-mypy) if not already done and run:

```bash
mypy src
```

## Known limitations

- The right hand side of a type rule is represented as a group entry. In other words, it uses the same structure as the right hand side of a group rule.
- A type wrapped into parentheses is represented as a group.
- AST nodes have properties that encode their semantics, as well as a list of children that they contain. The list of children includes all tokens that were consumed, including comments, and is used to serialize the node. The other semantics make processing more friendly. Updating semantics does not update the list of children. And updating the list of children does not update semantics.
- Parsing of strings and byte strings may not be fully correct. See also [RFC 9862](https://www.rfc-editor.org/rfc/rfc9682.html) for CDDL grammar updates.
- Overall, the AST is verbose and could be simplified.

## Acknowledgments

This implementation started as a direct port of the [CDDL parser in Node.js](https://github.com/christian-bromann/cddl) written by @christian-bromann (released under an MIT license), and the lexer remains largely equivalent to the Node.js one (but also supports additional productions such as byte strings). The parser is no longer a direct port: the Node.js parser does not support all productions allowed by the CDDL grammar and the goal here is to allow serializing the abstract syntax tree back into a string while preserving the original formatting (including whitespaces and comments).

This implementation follows the CDDL grammar more closely, making it closer to the [cddl-rs](https://github.com/anweiss/cddl) implementation in Rust by @anweiss (also released under an MIT license). As opposed to cddl-rs, this implementation does not validate CDDL blocks per se. It will only raise an error when a production cannot be parsed according to the grammar.

This implementation uses test files from these projects to validate the parser.
