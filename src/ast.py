from __future__ import annotations
from enum import StrEnum
from typing import Literal
from dataclasses import dataclass
from .tokens import Token

class Types(StrEnum):
    # any types
    ANY = 'any'

    # boolean types
    # Boolean value (major type 7, additional information 20 or 21).
    BOOL = 'bool'

    # numeric types
    # An unsigned integer or a negative integer.
    INT = 'int'
    # An unsigned integer (major type 0).
    UINT = 'uint'
    # A negative integer (major type 1).
    NINT = 'nint'
    # One of float16, float32, or float64.
    FLOAT = 'float'
    # A number representable as an IEEE 754 half-precision float
    FLOAT16 = 'float16'
    # A number representable as an IEEE 754 single-precision
    FLOAT32 = 'float32'
    # A number representable as an IEEE 754 double-precision
    FLOAT64 = 'float64'

    # string types
    # A byte string (major type 2).
    BSTR = 'bstr'
    # A byte string (major type 2).
    BYTES = 'bytes'
    # Text string (major type 3)
    TSTR = 'tstr'
    # Text string (major type 3)
    TEXT = 'text'

    # null types
    NIL = 'nil'
    NULL = 'null'

class ParentNode:
    '''
    To allow re-serialization of the abstract syntax tree in a way that
    preserves whitespaces, the parser needs to record the list of tokens that
    were used to compile each node.

    In practice, this is done by linking nodes through an actual tree
    structure, using Token as the leaf class.

    To ease more semantic uses of the tree, nodes also contain more concrete
    and directly useful properties. For example, a Group "name" will be the
    IDENT token child of the node, but it's also recorded in the "name"
    property.
    '''
    children: list[AstNode] = []

    def __init__(self) -> None:
        self.children = []

    def str(self) -> str:
        return ''.join([child.str() for child in self.children])

AstNode = ParentNode | Token

@dataclass
class CDDLTree(ParentNode):
    '''
    Represents a set of CDDL rules
    '''
    rules: list[Rule]

    def __post_init__(self):
        super().__init__()

@dataclass
class Rule(ParentNode):
    '''
    A group definition
    ```
    person = {
        age: int,
        name: tstr,
        employer: tstr,
    }
    ```
    '''
    name: str
    isChoiceAddition: bool
    type: Type | GroupEntry

    def __post_init__(self):
        super().__init__()

@dataclass
class GroupEntry(ParentNode):
    '''
    A group entry
    '''
    occurrence: Occurrence
    key: Memberkey | None
    type: Type | Group

    def __post_init__(self):
        super().__init__()

@dataclass
class Group(ParentNode):
    '''
    A group, meaning a list of group choices
    '''
    groupChoices: list[GroupChoice]
    isMap: bool

    def __post_init__(self):
        super().__init__()

@dataclass
class GroupChoice(ParentNode):
    '''
    A group choice
    '''
    groupEntries: list[GroupEntry]

    def __post_init__(self):
        super().__init__()

@dataclass
class Array(ParentNode):
    '''
    An array
    ```
    [ city: tstr ]
    ```
    '''
    groupChoices: list[GroupChoice]

    def __post_init__(self):
        super().__init__()


@dataclass
class Tag(ParentNode):
    '''
    A tag definition
    ```
    #6.32(tstr)
    ```
    '''
    numericPart: float | int | None = None
    typePart: Type | None = None

    def __post_init__(self):
        super().__init__()

@dataclass
class Comment(ParentNode):
    '''
    a comment statement
    ```
    ; This is a comment
    ```
    '''
    content: str
    leading: bool

    def __post_init__(self):
        super().__init__()

@dataclass
class Occurrence(ParentNode):
    n: int | float
    m: int | float

    def __post_init__(self):
        super().__init__()

@dataclass
class Value(ParentNode):
    '''
    A value (number, text or bytes)
    '''
    value: str
    type: Literal['number', 'text', 'bytes']

    def __post_init__(self):
        super().__init__()

@dataclass
class Typename(ParentNode):
    '''
    A typename (or groupname)
    '''
    name: str
    unwrapped: bool

    def __post_init__(self):
        super().__init__()

@dataclass
class Reference(ParentNode):
    '''
    A reference to another production
    '''
    target: Group | Typename

    def __post_init__(self):
        super().__init__()

# A type2 production is one of a few possibilities
Type2 = Value | Typename | Group | Array | Reference | Tag

@dataclass
class Range(ParentNode):
    '''
    A Range is a specific kind of Type1.

    The grammar allows a range boundary to be a Type2. In practice, it can only
    be an integer, a float, or a reference to a value that holds an integer or
    a float.
    '''
    min: Value | Typename
    max: Value | Typename
    inclusive: bool

    def __post_init__(self):
        super().__init__()

'''
Known control operators

Note: We may want to relax the check, control operators provide an extension
point for specs that define CDDL and they may define their own operators.
'''
OperatorName = Literal[
    # Control operators defined in the main CDDL spec
    'and', 'bits', 'cbor', 'cborseq', 'default',
    'eq', 'ge', 'gt', 'le', 'lt', 'ne',
    'regexp', 'size', 'within',

    # Not a default control operator but proposed in:
    # https://datatracker.ietf.org/doc/html/draft-bormann-cbor-cddl-freezer-14#name-control-operator-pcre
    'pcre'
]

@dataclass
class Operator(ParentNode):
    '''
    An operator is a specific type of Type1
    '''
    type: Type2
    name: OperatorName
    controller: Type2

    def __post_init__(self):
        super().__init__()

# A Type1 production is either a Type2, a Range or an Operator
Type1 = Type2 | Range | Operator


@dataclass
class Memberkey(ParentNode):
    type: Type1
    hasCut: bool

    def __post_init__(self):
        super().__init__()

@dataclass
class Type(ParentNode):
    '''
    A Type is a list of Type1, each representing a possible choice.
    '''
    types: list[Type1]

    def __post_init__(self):
        super().__init__()
