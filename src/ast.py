from __future__ import annotations
from enum import StrEnum
from typing import Literal
from dataclasses import dataclass, field
from .tokens import Token, Tokens

'''
Possible value types
'''
ValueType = Literal[
    'number', 'text', 'bytes', 'hex', 'base64'
]

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

    # Control operators defined in RFC9165:
    # https://datatracker.ietf.org/doc/html/rfc9165
    'plus', 'cat', 'det', 'abnf', 'abnfb', 'feature',

    # proposed in the freezer:
    # https://datatracker.ietf.org/doc/html/draft-bormann-cbor-cddl-freezer-14#name-control-operator-pcre
    'pcre'
]

class CDDLNode:
    '''
    Abstract base class for all nodes in the abstract syntax tree.
    '''
    def serialize(self, marker: Marker | None = None) -> str:
        return self._serialize(marker)

    def _serialize(self, marker: Marker | None = None) -> str:
        '''
        Function must be implemented in all subclasses
        '''
        raise Exception('_serialize method must be implemented in subclass')

    def _serializeToken(self, token: Token | None, marker: Marker | None = None) -> str:
        if token is None:
            return ''
        if marker is None:
            return token.serialize()
        return marker.markToken(token, self)

class WrappedNode(CDDLNode):
    '''
    A wrapped node is a node optionally enclosed in an open and close token.
    '''
    openToken: Token | None = None
    closeToken: Token | None = None

    def serialize(self, marker: Marker | None = None) -> str:
        output: str = self._serializeToken(self.openToken, marker)
        output += self._serialize(marker)
        output += self._serializeToken(self.closeToken, marker)
        return output

class TokenNode(WrappedNode):
    '''
    A token node is a node that essentially represents a concrete token and/or
    that may be part of a list.

    It stores the comments and whitespaces that may come *before* it, and an
    optional separator token that may be used *after* it to separate it from
    the next token in an underlying list.

    The separator remains None when the node is not part of a list, or not part
    of a list that uses separators.

    A token node is a wrapped node if its openToken and closeToken properties
    are set.
    '''
    # Comments and whitespace *before* the node
    comments: list[Token] = []
    whitespace: str = ''
    separator: Token | None = None

    def __init__(self) -> None:
        self.comments = []
        self.whitespace = ''
        self.separator = None

    def _prestr(self, marker: Marker | None = None) -> str:
        '''
        Function may be useful in subclasses to output something
        before the comments and whitespace associated with the
        main token
        '''
        return ''

    def serialize(self, marker: Marker | None = None) -> str:
        output = self._prestr(marker)
        for comment in self.comments:
            output += self._serializeToken(comment, marker)
        output += self.whitespace
        output += super().serialize(marker)
        output += self._serializeToken(self.separator, marker)
        return output

    def setComments(self, token: Token) -> None:
        self.comments = token.comments
        self.whitespace = token.whitespace

@dataclass
class CDDLTree(TokenNode):
    '''
    Represents a set of CDDL rules
    '''
    rules: list[Rule]

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        return ''.join([item.serialize(marker) for item in self.rules])

@dataclass
class Rule(CDDLNode):
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
    # Note: Consider storing as more directly useful booleans instead of as an
    # ASSIGN, TCHOICEALT or GCHOICEALT token (needed for spaces and comments)
    assign: Token
    type: Type | GroupEntry

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        output = self.name.serialize(marker)
        output += self._serializeToken(self.assign, marker)
        output += self.type.serialize(marker)
        return output

@dataclass
class GroupEntry(TokenNode):
    '''
    A group entry
    '''
    occurrence: Occurrence | None
    key: Memberkey | None
    type: Type | Group

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        output = ''
        if self.occurrence is not None:
            output += self.occurrence.serialize(marker)
        if self.key is not None:
            output += self.key.serialize(marker)
        output += self.type.serialize(marker)
        return output

@dataclass
class Group(TokenNode):
    '''
    A group, meaning a list of group choices wrapped in parentheses or curly
    braces
    '''
    groupChoices: list[GroupChoice]
    isMap: bool

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        return ''.join([item.serialize(marker) for item in self.groupChoices])

@dataclass
class GroupChoice(TokenNode):
    '''
    A group choice
    '''
    groupEntries: list[GroupEntry]

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        return ''.join([item.serialize(marker) for item in self.groupEntries])

@dataclass
class Array(TokenNode):
    '''
    An array
    ```
    [ city: tstr ]
    ```
    '''
    groupChoices: list[GroupChoice]

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        return ''.join([item.serialize(marker) for item in self.groupChoices])


@dataclass
class Tag(TokenNode):
    '''
    A tag definition
    ```
    #6.32(tstr)
    ```
    '''
    # TODO: consider storing the numeric part as an int or float instead of as
    # a NUMBER or FLOAT token (using Token for spaces and comments)
    numericPart: Token | None = None
    # TODO: Consider getting back to a Type, storing spaces and comments before
    # closing ")" separately, because a Group is fairly verbose
    # (use of a group means one can only access the type through:
    # typePart.groupChoices[0].groupEntries[0].type)
    typePart: Group | None = None

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        output: str = self._serializeToken(Token(Tokens.HASH, ''), marker)
        output += self._serializeToken(self.numericPart, marker)
        output += self.typePart.serialize(marker) if self.typePart is not None else ''
        return output

@dataclass
class Occurrence(TokenNode):
    n: int | float
    m: int | float
    # TODO: ideally, we wouldn't have the parser store tokens on top of
    # the min and max, that's just a quick and dirty way to get the
    # different combinations right
    tokens: list[Token] = field(default_factory=list)

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        return ''.join([self._serializeToken(item, marker) for item in self.tokens])


@dataclass
class Value(TokenNode):
    '''
    A value (number, text or bytes)
    '''
    value: str
    type: ValueType

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        prefix: str = ''
        suffix: str = ''
        if self.type == 'text':
            prefix = '"'
            suffix = '"'
        elif self.type == 'bytes':
            prefix = '\''
            suffix = '\''
        elif self.type == 'hex':
            prefix = 'h\''
            suffix = '\''
        elif self.type == 'base64':
            prefix = 'b64\''
            suffix = '\''
        if marker is None:
            return prefix + self.value + suffix
        else:
            return marker.markValue(prefix, self.value, suffix, self.type)

@dataclass
class Typename(TokenNode):
    '''
    A typename (or groupname)
    '''
    name: str
    unwrapped: Token | None
    parameters: GenericParameters | GenericArguments | None = None

    def __post_init__(self):
        super().__init__()

    def _prestr(self, marker: Marker | None = None) -> str:
        return self._serializeToken(self.unwrapped, marker)

    def _serialize(self, marker: Marker | None = None) -> str:
        output = ''
        if marker is None:
            output = self.name
        else:
            output += marker.markTypename(self.name, self)
        if self.parameters is not None:
            output += self.parameters.serialize(marker)
        return output

@dataclass
class Reference(TokenNode):
    '''
    A reference to another production
    '''
    target: Group | Typename

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        output: str = self._serializeToken(Token(Tokens.AMPERSAND, ''), marker)
        output += self.target.serialize(marker)
        return output

# A type2 production is one of a few possibilities
Type2 = Value | Typename | Group | Array | Reference | Tag

@dataclass
class Range(TokenNode):
    '''
    A Range is a specific kind of Type1.

    The grammar allows a range boundary to be a Type2. In practice, it can only
    be an integer, a float, or a reference to a value that holds an integer or
    a float.
    '''
    min: Value | Typename
    max: Value | Typename
    # TODO: would be better to store that as an "inclusive" bool. Using a Token
    # for now to store spaces and comments
    rangeop: Token

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        output = self.min.serialize(marker)
        output += self._serializeToken(self.rangeop, marker)
        output += self.max.serialize(marker)
        return output

@dataclass
class Operator(TokenNode):
    '''
    An operator is a specific type of Type1
    '''
    type: Type2
    # TODO: Consider storing operator as str. Using Token for spaces and
    # comments but Token is of type CTLOP and literal in OperatorName
    name: Token
    controller: Type2

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        output = self.type.serialize(marker)
        output += self._serializeToken(self.name, marker)
        output += self.controller.serialize(marker)
        return output

# A Type1 production is either a Type2, a Range or an Operator
Type1 = Type2 | Range | Operator


@dataclass
class Memberkey(CDDLNode):
    type: Type1
    hasCut: bool
    # TODO: ideally, we wouldn't have the parser store tokens on top of
    # the type and hasCut, that's just a quick and dirty way to get the
    # different combinations of cut tokens right (with spaces and comments)
    tokens: list[Token] = field(default_factory=list)

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        output = self.type.serialize(marker)
        output += ''.join([self._serializeToken(token, marker) for token in self.tokens])
        return output

@dataclass
class Type(CDDLNode):
    '''
    A Type is a list of Type1, each representing a possible choice.
    '''
    types: list[Type1]

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        return ''.join([item.serialize(marker) for item in self.types])

@dataclass
class GenericParameters(WrappedNode):
    '''
    A set of generic parameters
    '''
    parameters: list[Typename]

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        return ''.join([item.serialize(marker) for item in self.parameters])

@dataclass
class GenericArguments(WrappedNode):
    '''
    A set of generic arguments
    '''
    parameters: list[Type1]

    def __post_init__(self):
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        return ''.join([item.serialize(marker) for item in self.parameters])

class Marker():
    '''
    Base class to markup nodes during serialization.
    '''

    def markToken(self, token: Token, node: CDDLNode) -> str:
        '''
        Mark a Token.

        The function must handle whitespaces and comments that the Token
        contains.
        '''
        return token.serialize()

    def markValue(self, prefix: str, value: str, suffix: str, type: str) -> str:
        '''
        Mark a Value.
        '''
        return prefix + value + suffix

    def markTypename(self, name: str, node: CDDLNode) -> str:
        '''
        Mark a typename or a groupname
        '''
        return name
