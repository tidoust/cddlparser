# A CDDL parser in Python

> Concise data definition language ([RFC 8610](https://datatracker.ietf.org/doc/html/rfc8610)) parser implementation in Python.

CDDL expresses Concise Binary Object Representation (CBOR) data structures ([RFC 7049](https://datatracker.ietf.org/doc/html/rfc7049)). Its main goal is to provide an easy and unambiguous way to express structures for protocol messages and data formats that use CBOR or JSON.

This Python implementation provides a CDDL parser suitable for producing marked up serializations of the CDDL. It is intended to be used in spec authoring tools to add cross-referencing logic within CDDL blocks.

## Usage

### How to install

Clone the repository:

```bash
git clone https//github.com/tidoust/cddlparser
```

### Command-line interface

Run `cddlparser.py`, passing in the path to a CDDL file as parameter

```bash
python cddlparser.py tests/__fixtures__/example.cddl
```

That should print a serialization of the [Abstract Syntax Tree](https://en.wikipedia.org/wiki/Abstract_syntax_tree) (AST) produced by the parser, followed by a re-serialization of the AST, which should match the original file.

### As a Python package

The parser is available as a [Pypi package](https://pypi.org/project/cddlparser/). To install the package, run:

```bash
pip install cddlparser
```

You should then be able to write code such as:

```python
from cddlparser import parse
from prettyprint import pprint
ast = parse('''
  person = {
      identity,                         ; an identity
      employer: tstr,                   ; some employer
  }''')

print('The Abstract syntax tree:')
pprint(ast)

print()
print('Re-serialization:')
print(ast.serialize())
```

To create markup during serialization, you need to pass an object that subclasses the `Marker` class (see inline notes for a bit of documentation).

```python
from cddlparser import parse
from cddlparser.ast import CDDLNode, Marker, Markup, Rule

class StrongNameMarker(Marker):
    def serializeName(self, name: str, node: CDDLNode) -> str:
        return '<b>' + name + '</b>'

    def markupFor(self, node: CDDLNode) -> Markup:
        if isinstance(node, Rule):
            return ('<div class="rule">', '</div>')
        return super().markupFor(node)

ast = parse('''person = {
  identity,
  employer: tstr,
}''')

print(ast.serialize(StrongNameMarker()))
```

This should produce:

```html
<div class="rule"><b>person</b> = {
  <b>identity</b>,
  <b>employer</b>: <b>tstr</b>,
}</div>
```

## How to run tests

You may run tests from a local copy of the code:

```bash
python tests.py
```

Parser tests compare the AST produced by the parser with a serialized snapshot of the expected AST. If you make changes to the parser and need to refresh a snapshot, delete the corresponding `tests/__snapshots__/[test].snap` file and run tests again.

Parser tests also compare the result of serializing the AST with the initial input.

The test files are a combination of the test files used in the other CDDL parser projects mentioned:
- [Test files from cddl-rs](https://github.com/anweiss/cddl/tree/main/tests/fixtures/cddl).
- [Test files from cddl](https://github.com/christian-bromann/cddl/tree/main/tests/__fixtures__), with a couple of fixes.

The code uses static types. To validate types and code, install [`mypy`](https://mypy.readthedocs.io/en/stable/getting_started.html#installing-and-running-mypy), [ruff](https://docs.astral.sh/ruff/), [black](https://black.readthedocs.io/en/stable/index.html) and [pylint](https://www.pylint.org/) if not already done and run:

```bash
mypy cddlparser
ruff check
black .
pylint cddlparser
```

## Known limitations

- Updates to the CDDL grammar defined in [RFC 9862](https://www.rfc-editor.org/rfc/rfc9682.html) are not supported.
- The parser validates the CDDL syntax against the CDDL grammar. It also validates that there are no obvious type/group inconsistencies. The parser does not validate the CDDL beyond that. For example, the parser does not choke if two rules have the same name but define different types.
- The only logic that exists in the AST for now is the serialization logic. There are no facilities to import CDDL modules, resolve references, inline groups, validate CBOR, etc.
- The parser does not fully understand when a rule defines a type and when it defines a group. It may represent the right hand side of a type definition as a `GroupEntry` node, instead of as a `Type` node.
- Overall, the AST is verbose and could be simplified.

## Acknowledgments

This `cddlparser` Python module merely came into existence because I needed a CDDL parser in Python that I could leverage to add CDDL support in [Bikeshed](https://github.com/speced/bikeshed) (not done yet!) and could not find any. I took inspiration from existing CDDL parsers written in other languages:

- [`cddl`](https://github.com/christian-bromann/cddl): a JavaScript implementation of a CDDL parser for Node.js, released under an MIT license, written by @christian-bromann. `cddlparser` started as a direct port of the JavaScript code, and the lexer remains similar to the JavaScript one. Testing structures and main test files also come from `cddl`. The parser in `cddlparser` is completely different though, given the need to preserve the original formatting (including whitespaces and comments) to re-serialize the AST back into a string.
- [`cddl-rs`](https://github.com/anweiss/cddl): a Rust implementation of a CDDL parser, released under an MIT license, written by @anweiss, that features a CDDL validator. The parser in `cddlparser` follows a similar "close to the CDDL grammar" logic. The `cddlparser` test suite also contains test files from the `cddl-rs` project.
- [`cddlc`](https://github.com/cabo/cddlc): A set of CDDL utilities written in Ruby by @cabo, along with CDDL extracts from IETF RFCs. The `cddlparser` test suite makes sure that CDDL extracts in the `cddlc` repository can be parsed and serialized again.
