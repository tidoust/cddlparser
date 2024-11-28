from __future__ import annotations
from enum import StrEnum
from typing import Literal
from dataclasses import dataclass
from .tokens import Token

class AstNode:
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
    children: list[CDDLNode] = []

    def __init__(self) -> None:
        self.children = []

    def str(self) -> str:
        return ''.join([child.str() for child in self.children])

CDDLNode = AstNode | Token

@dataclass
class CDDLTree(AstNode):
    '''
    Represents a set of CDDL rules
    '''
    rules: list[Rule]

    def __post_init__(self):
        super().__init__()

@dataclass
class Rule(AstNode):
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
    name: Typename
    isChoiceAddition: bool
    type: Type | GroupEntry

    def __post_init__(self):
        super().__init__()

@dataclass
class GroupEntry(AstNode):
    '''
    A group entry
    '''
    occurrence: Occurrence
    key: Memberkey | None
    type: Type | Group

    def __post_init__(self):
        super().__init__()

@dataclass
class Group(AstNode):
    '''
    A group, meaning a list of group choices wrapped in parentheses or curly
    braces
    '''
    groupChoices: list[GroupChoice]
    isMap: bool

    def __post_init__(self):
        super().__init__()

@dataclass
class GroupChoice(AstNode):
    '''
    A group choice
    '''
    groupEntries: list[GroupEntry]

    def __post_init__(self):
        super().__init__()

@dataclass
class Array(AstNode):
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
class Tag(AstNode):
    '''
    A tag definition
    ```
    #6.32(tstr)
    ```
    '''
    numericPart: float | int | None = None
    # TODO: Consider getting back to a Type, storing spaces and comments before
    # closing ")" separately, because a Group is fairly verbose
    # (use of a group means one can only access the type through:
    # typePart.groupChoices[0].groupEntries[0].type)
    typePart: Group | None = None

    def __post_init__(self):
        super().__init__()

@dataclass
class Occurrence(AstNode):
    n: int | float
    m: int | float

    def __post_init__(self):
        super().__init__()

@dataclass
class Value(AstNode):
    '''
    A value (number, text or bytes)
    '''
    value: str
    type: Literal['number', 'text', 'bytes', 'hex', 'base64']

    def __post_init__(self):
        super().__init__()

@dataclass
class Typename(AstNode):
    '''
    A typename (or groupname)
    '''
    name: str
    unwrapped: bool
    parameters: GenericParameters | GenericArguments | None = None

    def __post_init__(self):
        super().__init__()

@dataclass
class Reference(AstNode):
    '''
    A reference to another production
    '''
    target: Group | Typename

    def __post_init__(self):
        super().__init__()

# A type2 production is one of a few possibilities
Type2 = Value | Typename | Group | Array | Reference | Tag

@dataclass
class Range(AstNode):
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
class Operator(AstNode):
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
class Memberkey(AstNode):
    type: Type1
    hasCut: bool

    def __post_init__(self):
        super().__init__()

@dataclass
class Type(AstNode):
    '''
    A Type is a list of Type1, each representing a possible choice.
    '''
    types: list[Type1]

    def __post_init__(self):
        super().__init__()

@dataclass
class GenericParameters(AstNode):
    '''
    A set of generic parameters
    '''
    parameters: list[Typename]

    def __post_init__(self):
        super().__init__()

@dataclass
class GenericArguments(AstNode):
    '''
    A set of generic arguments
    '''
    parameters: list[Type1]

    def __post_init__(self):
        super().__init__()
