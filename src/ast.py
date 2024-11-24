from __future__ import annotations
from enum import StrEnum
from typing import Literal, Optional
from dataclasses import dataclass
from .tokens import Token

class Type(StrEnum):
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
class Group(ParentNode):
    '''
    a group definition
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
    properties: list[Property|list[Property]]
    comments: list[Comment]
    operator: Optional[Operator] = None
    type: Literal['group'] = 'group'

    def __post_init__(self):
        super().__init__()

@dataclass
class Array(ParentNode):
    '''
    an array definition
    ```
    Geography = [
        city: tstr
    ]
    ```
    '''
    name: str
    values: list[Property|list[Property]]
    comments: list[Comment]
    type: Literal['array'] = 'array'

    def __post_init__(self):
        super().__init__()

@dataclass
class Tag(ParentNode):
    '''
    a tag definition
    ```
    #6.32(tstr)
    ```
    '''
    numericPart: float | int
    typePart: str

    def __post_init__(self):
        super().__init__()

@dataclass
class Variable(ParentNode):
    '''
    a variable assignment
    ```
    device-address = byte
    ```
    '''
    name: str
    isChoiceAddition: bool
    propertyType: PropertyType | PropertyTypes
    comments: list[Comment]
    operator: Optional[Operator] = None
    type: Literal['variable'] = 'variable'

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
    type: Literal['comment'] = 'comment'

    def __post_init__(self):
        super().__init__()

@dataclass
class Occurrence(ParentNode):
    n: int | float
    m: int | float

    def __post_init__(self):
        super().__init__()

@dataclass
class Property(ParentNode):
    hasCut: bool
    occurrence: Occurrence
    name: str
    type: PropertyType | PropertyTypes
    comments: list[Comment]
    operator: Optional[Operator] = None

    def __post_init__(self):
        super().__init__()

'''
can be a number, e.g. "foo = 0..10"
```
{
  Type: "int",
  Value: 6
}
```
or a literal, e.g. "foo = 0..max-byte"
```
{
  Type: "literal",
  Value: "max-byte"
}
```
'''
RangePropertyReference = float | int | str

@dataclass
class Range(ParentNode):
    min: RangePropertyReference
    max: RangePropertyReference
    inclusive: bool

    def __post_init__(self):
        super().__init__()

OperatorType = Literal['default', 'size', 'regexp', 'bits', 'and', 'within', 'eq', 'ne', 'lt', 'le', 'gt', 'ge']

@dataclass
class Operator(ParentNode):
    type: OperatorType
    value: PropertyType

    def __post_init__(self):
        super().__init__()

PropertyReferenceType = Literal['literal', 'group', 'group_array', 'array', 'range', 'tag']

@dataclass
class PropertyReference(ParentNode):
    type: PropertyReferenceType
    value: str | float | int | bool | Group | Array | Range | Tag
    unwrapped: bool
    operator: Optional[Operator] = None

    def __post_init__(self):
        super().__init__()

@dataclass
class StrPropertyType(ParentNode):
    value: str

@dataclass
class NativeTypeWithOperator(ParentNode):
    type: StrPropertyType | PropertyReference
    operator: Optional[Operator] = None

    def __init__(self, type: StrPropertyType | PropertyReference, operator: Optional[Operator] = None):
        self.type = type
        self.operator = operator
        self.children = [type]
        if operator is not None:
            self.children.append(operator)

Assignment = Group | Array | Variable
PropertyType = Assignment | PropertyReference | StrPropertyType | NativeTypeWithOperator

@dataclass
class PropertyTypes(ParentNode):
    types: list[PropertyType]

@dataclass
class CDDLTree:
    '''
    Represents a set of CDDL assignments
    '''
    assignments: list[Assignment]

    def str(self) -> str:
        return ''.join([child.str() for child in self.assignments])