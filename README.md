# A CDDL parser in Python

> Concise data definition language ([RFC 8610](https://datatracker.ietf.org/doc/html/rfc8610)) parser implementation in Python.

CDDL expresses Concise Binary Object Representation (CBOR) data structures ([RFC 7049](https://datatracker.ietf.org/doc/html/rfc7049)). Its main goal is to provide an easy and unambiguous way to express structures for protocol messages and data formats that use CBOR or JSON.

This Python implementation provides a CDDL parser suitable for producing marked up serializations of the CDDL. It is intended to be used in spec authoring tools to add cross-referencing logic within CDDL blocks that the specs may define.

This implementation started a direct port of the [CDDL parser in Node.js](https://github.com/christian-bromann/cddl) written by @christian-bromann, released under an MIT license. The lexer remains mainly equivalent to its Node.js counterpart, with a few additions to handle `=>`, `//`, `/=`, `//=`, and control operators directly. To keep flexibility and make it easier to re-serialize the abstract syntax tree into a string that preserves initial whitespaces and comments, the parser has a different logic and follows the CDDL grammar more closely. This makes it closer to the [cddl-rs](https://github.com/anweiss/cddl) implementation in Rust by @anweiss, but note this implementation does not validate CDDL blocks in any way (and will happily accept blocks that are not valid).

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

The code uses static types. To validate types, [install `mypy`](https://mypy.readthedocs.io/en/stable/getting_started.html#installing-and-running-mypy) if not already done and run:

```bash
mypy src
```

## Known limitations

- No support for [generics](https://datatracker.ietf.org/doc/html/rfc8610#section-3.10).
- The right hand side of a type rule is represented as a group entry. In other words, it uses the same structure as the right hand side of a group rule.
- A type wrapped into parentheses is represented as a group.
- AST nodes have properties that encode their semantics, as well as a list of children that they contain. The list of children includes all tokens that were consumed, including comments, and is used to serialize the node. The other semantics make processing more friendly. Updating semantics does not update the list of children. And updating the list of children does not update semantics.
- Overall, the AST is verbose and could be simplified.