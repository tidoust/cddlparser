from __future__ import annotations
from enum import StrEnum
from typing import Literal, Optional
from dataclasses import dataclass

@dataclass
class Group:
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
    type: Literal['group'] = 'group'

@dataclass
class Array:
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

@dataclass
class Tag:
    '''
    a tag definition
    ```
    #6.32(tstr)
    ```
    '''
    numericPart: float | int
    typePart: str

@dataclass
class Variable:
    '''
    a variable assignment
    ```
    device-address = byte
    ```
    '''
    name: str
    isChoiceAddition: bool
    propertyType: PropertyType | list[PropertyType]
    comments: list[Comment]
    operator: Optional[Operator] = None
    type: Literal['variable'] = 'variable'

@dataclass
class Comment:
    '''
    a comment statement
    ```
    ; This is a comment
    ```
    '''
    content: str
    leading: bool
    type: Literal['comment'] = 'comment'

@dataclass
class Occurrence:
    n: int
    m: int
    def __init__(self, n, m):
        self.n = n
        self.m = m

@dataclass
class Property:
    hasCut: bool
    occurrence: Occurrence
    name: PropertyName
    type: PropertyType | list[PropertyType]
    comments: list[Comment]
    operator: Optional[Operator] = None

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
class Range:
    min: RangePropertyReference
    max: RangePropertyReference
    inclusive: bool

OperatorType = Literal['default', 'size', 'regexp', 'bits', 'and', 'within', 'eq', 'ne', 'lt', 'le', 'gt', 'ge']

@dataclass
class Operator:
    type: OperatorType
    value: PropertyType

PropertyReferenceType = Literal['literal', 'group', 'group_array', 'array', 'range', 'tag']

@dataclass
class PropertyReference:
    type: PropertyReferenceType
    value: str | float | int | bool | Group | Array | Range | Tag
    unwrapped: bool
    operator: Optional[Operator] = None

@dataclass
class NativeTypeWithOperator:
    type: str | PropertyReference
    operator: Optional[Operator] = None

Assignment = Group | Array | Variable
PropertyType = Assignment | Array | PropertyReference | str | NativeTypeWithOperator
PropertyName = str