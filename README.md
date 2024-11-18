# A CDDL parser in Python

> Concise data definition language ([RFC 8610](https://tools.ietf.org/html/rfc8610)) parser implementation in Python.

CDDL expresses Concise Binary Object Representation (CBOR) data structures ([RFC 7049](https://tools.ietf.org/html/rfc7049)). Its main goal is to provide an easy and unambiguous way to express structures for protocol messages and data formats that use CBOR or JSON.

This Python implementation is a direct port of the [CDDL parser in Node.js](https://github.com/christian-bromann/cddl) written by @christian-bromann, released under an MIT license.

There are also CDDL parsers for other languages:
- Node.js: [christian-bromann/cddl](https://github.com/christian-bromann/cddl)
- Rust: [anweiss/cddl](https://github.com/anweiss/cddl)

__Note:__ This is __work in progress__ and the underlyling Node.js parser is __also__ work in progress. Feel free to have a look at the code and report problems, but you may not want to rely on the code.

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

That should print a serialization of the [Abstract Syntax Tree](https://en.wikipedia.org/wiki/Abstract_syntax_tree) (AST) produced by the parser. For example:

```
[Group(name='person',
       isChoiceAddition=False,
       properties=[Property(hasCut=False,
                            occurrence=Occurrence(n=1, m=1),
                            name='',
                            type=[PropertyReference(type='group',
                                                    value='identity',
                                                    unwrapped=False,
                                                    operator=None)],
                            comments=[Comment(content='an identity',
                                              leading=False,
                                              type='comment')],
                            operator=None),
                   Property(hasCut=True,
                            occurrence=Occurrence(n=1, m=1),
                            name='employer',
                            type=['tstr'],
                            comments=[Comment(content='some employer',
                                              leading=False,
                                              type='comment')],
                            operator=None)],
       comments=[],
       type='group')]
```


## How to run tests

```bash
python tests.py
```

Parser tests compare the AST produced by the parser with a serialized snapshot of the expected AST. If you make changes to the parser and need to refresh a snapshot, delete the corresponding `tests/__snapshots__/[test].snap` file and run tests again.

The code uses static types. To validate types, [install `mypy`](https://mypy.readthedocs.io/en/stable/getting_started.html#installing-and-running-mypy) if not already done and run:

```bash
mypy src
```
