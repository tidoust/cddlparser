from __future__ import annotations
from typing import Literal, Sequence, Union, Optional
from dataclasses import dataclass, field
from .tokens import Token, Tokens

# Possible value types
ValueType = Literal["number", "text", "bytes", "hex", "base64"]

# Known control operators
#
# Note: We may want to relax the check, control operators provide an extension
# point for specs that define CDDL and they may define their own operators.
OperatorName = Literal[
    # Control operators defined in the main CDDL spec
    "and",
    "bits",
    "cbor",
    "cborseq",
    "default",
    "eq",
    "ge",
    "gt",
    "le",
    "lt",
    "ne",
    "regexp",
    "size",
    "within",
    # Control operators defined in RFC9165:
    # https://datatracker.ietf.org/doc/html/rfc9165
    "plus",
    "cat",
    "det",
    "abnf",
    "abnfb",
    "feature",
    # proposed in the freezer:
    # https://datatracker.ietf.org/doc/html/draft-bormann-cbor-cddl-freezer-14#name-control-operator-pcre
    "pcre",
]

# Prelude types defined in RFC810:
# https://datatracker.ietf.org/doc/html/rfc8610#appendix-D
PreludeType = Literal[
    "any",
    "uint",
    "nint",
    "int",
    "bstr",
    "bytes",
    "tstr",
    "text",
    "tdate",
    "time",
    "number",
    "biguint",
    "bignint",
    "bigint",
    "integer",
    "unsigned",
    "decfrac",
    "bigfloat",
    "eb64url",
    "eb64legacy",
    "eb16",
    "encoded-cbor",
    "uri",
    "b64url",
    "b64legacy",
    "regexp",
    "mime-message",
    "cbor-any",
    "float16",
    "float32",
    "float64",
    "float16-32",
    "float32-64",
    "float",
    "false",
    "true",
    "bool",
    "nil",
    "null",
    "undefined",
]


class CDDLNode:
    """
    Abstract base class for all nodes in the abstract syntax tree.
    """

    parentNode: CDDLNode | None = None

    def serialize(self, marker: Marker | None = None) -> str:
        # Make sure that parentNode relationships are properly set
        self.setChildrenParent()
        if marker is not None:
            markup = marker.markupFor(self)
            output = markup[0] if markup[0] is not None else ""
            output += self._serialize(marker)
            output += markup[1] if markup[1] is not None else ""
            return output
        return self._serialize()

    def setChildrenParent(self) -> None:
        """
        Initialize the parentNode links from children nodes to this node
        so that marker can access and adapt its behavior based on the
        current context.
        """
        for child in self.getChildren():
            child.parentNode = self
            child.setChildrenParent()

    def getChildren(self) -> Sequence[CDDLNode]:
        """
        Return the list of children nodes attached to this node
        """
        return []

    def _serialize(self, marker: Marker | None = None) -> str:
        """
        Function must be implemented in all subclasses.
        """
        raise NotImplementedError("_serialize method must be implemented in subclass")

    def _serializeToken(self, token: Token | None, marker: Marker | None = None) -> str:
        if token is None:
            return ""
        if marker is None:
            return token.serialize()
        return marker.serializeToken(token, self)

    def __repr__(self, indent: int = 0) -> str:
        return "  " * indent + self.__class__.__name__


class WrappedNode(CDDLNode):
    """
    A wrapped node is a node optionally enclosed in an open and close token.
    """

    openToken: Token | None = None
    closeToken: Token | None = None

    def serialize(self, marker: Marker | None = None) -> str:
        output = ""
        if marker is not None:
            markup = marker.markupFor(self)
            output += markup[0] if markup[0] is not None else ""
        output += self._serializeToken(self.openToken, marker)
        output += self._serialize(marker)
        output += self._serializeToken(self.closeToken, marker)
        if marker is not None:
            output += markup[1] if markup[1] is not None else ""
        return output

    def _serialize(self, marker: Marker | None = None) -> str:
        """
        Function must be implemented in all subclasses.
        """
        raise NotImplementedError("_serialize method must be implemented in subclass")

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [super().__repr__(indent)]
        if self.openToken is not None:
            res.append(self.openToken.__repr__(indent + 1))
        if self.closeToken is not None:
            res.append(self.closeToken.__repr__(indent + 1))
        return "\n".join(res)


class TokenNode(WrappedNode):
    """
    A token node is a node that essentially represents a concrete token and/or
    that may be part of a list.

    It stores the comments and whitespaces that may come *before* it, and an
    optional separator token that may be used *after* it to separate it from
    the next token in an underlying list.

    The separator remains None when the node is not part of a list, or not part
    of a list that uses separators.

    A token node is a wrapped node if its openToken and closeToken properties
    are set.
    """

    # Comments and whitespace *before* the node
    comments: list[Token] = []
    whitespace: str = ""
    separator: Token | None = None

    def __init__(self) -> None:
        self.comments = []
        self.whitespace = ""
        self.separator = None

    # pylint: disable=unused-argument
    def _prestr(self, marker: Marker | None = None) -> str:
        """
        Function may be useful in subclasses to output something
        before the comments and whitespace associated with the
        main token
        """
        return ""

    def _serialize(self, marker: Marker | None = None) -> str:
        """
        Function must be implemented in all subclasses.
        """
        raise NotImplementedError("_serialize method must be implemented in subclass")

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

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [super().__repr__(indent)]
        for comment in self.comments:
            res.append(comment.__repr__(indent + 1))
        if self.whitespace != "":
            res.append("  " * (indent + 1) + f"whitespaces: {len(self.whitespace)}")
        if self.separator is not None:
            res.append(self.separator.__repr__(indent + 1))
        return "\n".join(res)


@dataclass
class CDDLTree(TokenNode):
    """
    Represents a set of CDDL rules
    """

    rules: list[Rule]

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return self.rules

    def _serialize(self, marker: Marker | None = None) -> str:
        return "".join([item.serialize(marker) for item in self.rules])

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [super().__repr__(indent)]
        for rule in self.rules:
            res.append(rule.__repr__(indent + 1))
        return "\n".join(res)


@dataclass
class Rule(CDDLNode):
    """
    A group definition
    ```
    person = {
        age: int,
        name: tstr,
        employer: tstr,
    }
    ```
    """

    name: Typename
    # Note: Consider storing as more directly useful booleans instead of as an
    # ASSIGN, TCHOICEALT or GCHOICEALT token (needed for spaces and comments)
    assign: Token
    type: Type | GroupEntry

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return [self.name, self.type]

    def _serialize(self, marker: Marker | None = None) -> str:
        output = self.name.serialize(marker)
        output += self._serializeToken(self.assign, marker)
        output += self.type.serialize(marker)
        return output

    def __repr__(self, indent: int = 0) -> str:
        return "\n".join(
            [
                super().__repr__(indent),
                self.name.__repr__(indent + 1),
                self.assign.__repr__(indent + 1),
                self.type.__repr__(indent + 1),
            ]
        )


@dataclass
class GroupEntry(TokenNode):
    """
    A group entry
    """

    occurrence: Occurrence | None
    key: Memberkey | None
    type: Type

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        children: list[CDDLNode] = []
        if self.occurrence is not None:
            children.append(self.occurrence)
        if self.key is not None:
            children.append(self.key)
        children.append(self.type)
        return children

    def _serialize(self, marker: Marker | None = None) -> str:
        output = ""
        if self.occurrence is not None:
            output += self.occurrence.serialize(marker)
        if self.key is not None:
            output += self.key.serialize(marker)
        output += self.type.serialize(marker)
        return output

    def isConvertibleToType(self) -> bool:
        """
        Return true if GroupEntry can be converted to a proper Type.

        Essentially, the function returns true when the GroupEntry does not
        start with an occurrence production, does not define a member key,
        and has a Type that is not the "(" S group S ")" production (which
        we represent as a Type to simplify the parsing logic, but which isn't
        a proper Type.
        """
        return (
            self.occurrence is None
            and self.key is None
            and (
                not isinstance(self.type, Group) or isinstance(self.type, (Array, Map))
            )
        )

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [super().__repr__(indent)]
        if self.occurrence is not None:
            res.append(self.occurrence.__repr__(indent + 1))
        if self.key is not None:
            res.append(self.key.__repr__(indent + 1))
        res.append(self.type.__repr__(indent + 1))
        return "\n".join(res)


@dataclass
class Group(TokenNode):
    """
    A group, meaning a list of group choices wrapped in parentheses
    """

    groupChoices: list[GroupChoice]

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return self.groupChoices

    def _serialize(self, marker: Marker | None = None) -> str:
        return "".join([item.serialize(marker) for item in self.groupChoices])

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [super().__repr__(indent)]
        for item in self.groupChoices:
            res.append(item.__repr__(indent + 1))
        return "\n".join(res)


class Map(Group):
    """
    A map, meaning a list of group choices wrapped in curly braces
    """


class Array(Group):
    """
    An array
    ```
    [ city: tstr ]
    ```
    """


@dataclass
class GroupChoice(TokenNode):
    """
    A group choice
    """

    groupEntries: list[GroupEntry]

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return self.groupEntries

    def _serialize(self, marker: Marker | None = None) -> str:
        return "".join([item.serialize(marker) for item in self.groupEntries])

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [super().__repr__(indent)]
        for item in self.groupEntries:
            res.append(item.__repr__(indent + 1))
        return "\n".join(res)


@dataclass
class Tag(TokenNode):
    """
    A tag definition
    ```
    #6.32(tstr)
    ```
    """

    # TODO: consider storing the numeric part as an int or float instead of as
    # a NUMBER or FLOAT token (using Token for spaces and comments)
    numericPart: Token | None = None
    typePart: Type | None = None

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return [self.typePart] if self.typePart is not None else []

    def _serialize(self, marker: Marker | None = None) -> str:
        output: str = self._serializeToken(Token(Tokens.HASH, ""), marker)
        output += self._serializeToken(self.numericPart, marker)
        output += self.typePart.serialize(marker) if self.typePart is not None else ""
        return output

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [super().__repr__(indent) + " (#)"]
        if self.numericPart is not None:
            res.append(self.numericPart.__repr__(indent + 1))
        if self.typePart is not None:
            res.append(self.typePart.__repr__(indent + 1))
        return "\n".join(res)


@dataclass
class Occurrence(TokenNode):
    n: int | float
    m: int | float
    # TODO: ideally, we wouldn't have the parser store tokens on top of
    # the min and max, that's just a quick and dirty way to get the
    # different combinations right
    tokens: list[Token] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        return "".join([self._serializeToken(item, marker) for item in self.tokens])

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [super().__repr__(indent)]
        for item in self.tokens:
            res.append(item.__repr__(indent + 1))
        return "\n".join(res)


@dataclass
class Value(TokenNode):
    """
    A value (number, text or bytes)
    """

    value: str
    type: ValueType

    def __post_init__(self) -> None:
        super().__init__()

    def _serialize(self, marker: Marker | None = None) -> str:
        prefix: str = ""
        suffix: str = ""
        if self.type == "text":
            prefix = '"'
            suffix = '"'
        elif self.type == "bytes":
            prefix = "'"
            suffix = "'"
        elif self.type == "hex":
            prefix = "h'"
            suffix = "'"
        elif self.type == "base64":
            prefix = "b64'"
            suffix = "'"
        if marker is None:
            return prefix + self.value + suffix
        return marker.serializeValue(prefix, self.value, suffix, self)

    def __repr__(self, indent: int = 0) -> str:
        return "  " * indent + f"{self.__class__.__name__} ({self.type}): {self.value}"


@dataclass
class Typename(TokenNode):
    """
    A typename (or groupname)
    """

    name: str
    unwrapped: Token | None
    parameters: GenericParameters | GenericArguments | None = None

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return [self.parameters] if self.parameters is not None else []

    def _prestr(self, marker: Marker | None = None) -> str:
        return self._serializeToken(self.unwrapped, marker)

    def _serialize(self, marker: Marker | None = None) -> str:
        output = ""
        if marker is None:
            output = self.name
        else:
            output += marker.serializeName(self.name, self)
        if self.parameters is not None:
            output += self.parameters.serialize(marker)
        return output

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [super().__repr__(indent), ("  " * (indent + 1)) + self.name]
        if self.unwrapped is not None:
            res.append(self.unwrapped.__repr__(indent + 1))
        if self.parameters is not None:
            res.append(self.parameters.__repr__(indent + 1))
        return "\n".join(res)


@dataclass
class ChoiceFrom(TokenNode):
    """
    A choice built from a group (or a groupname)
    """

    target: Group | Typename

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return [self.target]

    def _serialize(self, marker: Marker | None = None) -> str:
        output: str = self._serializeToken(Token(Tokens.AMPERSAND, ""), marker)
        output += self.target.serialize(marker)
        return output

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [
            super().__repr__(indent) + " (&)",
            self.target.__repr__(indent + 1),
        ]
        return "\n".join(res)


# A type2 production is one of a few possibilities
# (Note the need to use a forward reference to resolve the circular dependency
# between Type and Type2, see:
# https://docs.python.org/3/library/stdtypes.html#types-union)
Type2 = Union[Value, Typename, "Type", Group, Map, Array, ChoiceFrom, Tag]


@dataclass
class Range(TokenNode):
    """
    A Range is a specific kind of Type1.

    The grammar allows a range boundary to be a Type2. In practice, it can only
    be an integer, a float, or a reference to a value that holds an integer or
    a float.
    """

    min: Value | Typename
    max: Value | Typename
    # TODO: would be better to store that as an "inclusive" bool. Using a Token
    # for now to store spaces and comments
    rangeop: Token

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return [self.min, self.max]

    def _serialize(self, marker: Marker | None = None) -> str:
        output = self.min.serialize(marker)
        output += self._serializeToken(self.rangeop, marker)
        output += self.max.serialize(marker)
        return output

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [
            super().__repr__(indent),
            self.min.__repr__(indent + 1),
            self.rangeop.__repr__(indent + 1),
            self.max.__repr__(indent + 1),
        ]
        return "\n".join(res)


@dataclass
class Operator(TokenNode):
    """
    An operator is a specific type of Type1
    """

    type: Type2
    # TODO: Consider storing operator as str. Using Token for spaces and
    # comments but Token is of type CTLOP and literal in OperatorName
    name: Token
    controller: Type2

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return [self.type, self.controller]

    def _serialize(self, marker: Marker | None = None) -> str:
        output = self.type.serialize(marker)
        output += self._serializeToken(self.name, marker)
        output += self.controller.serialize(marker)
        return output

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [
            super().__repr__(indent),
            self.type.__repr__(indent + 1),
            self.name.__repr__(indent + 1),
            self.controller.__repr__(indent + 1),
        ]
        return "\n".join(res)


# A Type1 production is either a Type2, a Range or an Operator
Type1 = Union[Type2, Range, Operator]


@dataclass
class Memberkey(CDDLNode):
    type: Type1
    hasCut: bool
    hasColon: bool
    # TODO: ideally, we wouldn't have the parser store tokens on top of
    # the type and hasCut, that's just a quick and dirty way to get the
    # different combinations of cut tokens right (with spaces and comments)
    tokens: list[Token] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return [self.type]

    def _serialize(self, marker: Marker | None = None) -> str:
        output = self.type.serialize(marker)
        output += "".join(
            [self._serializeToken(token, marker) for token in self.tokens]
        )
        return output

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [
            super().__repr__(indent),
            self.type.__repr__(indent + 1),
        ]
        for item in self.tokens:
            res.append(item.__repr__(indent + 1))
        return "\n".join(res)


@dataclass
class Type(TokenNode):
    """
    A Type is a list of Type1, each representing a possible choice.

    The Type construct can also represent a type wrapped in parentheses
    (hence why the class subclasses WrappedNode)
    """

    types: list[Type1]

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return self.types

    def _serialize(self, marker: Marker | None = None) -> str:
        return "".join([item.serialize(marker) for item in self.types])

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [super().__repr__(indent)]
        for item in self.types:
            res.append(item.__repr__(indent + 1))
        return "\n".join(res)


@dataclass
class GenericParameters(WrappedNode):
    """
    A set of generic parameters
    """

    parameters: list[Typename]

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return self.parameters

    def _serialize(self, marker: Marker | None = None) -> str:
        return "".join([item.serialize(marker) for item in self.parameters])

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [super().__repr__(indent)]
        for item in self.parameters:
            res.append(item.__repr__(indent + 1))
        return "\n".join(res)


@dataclass
class GenericArguments(WrappedNode):
    """
    A set of generic arguments
    """

    parameters: list[Type1]

    def __post_init__(self) -> None:
        super().__init__()

    def getChildren(self) -> Sequence[CDDLNode]:
        return self.parameters

    def _serialize(self, marker: Marker | None = None) -> str:
        return "".join([item.serialize(marker) for item in self.parameters])

    def __repr__(self, indent: int = 0) -> str:
        res: list[str] = [super().__repr__(indent)]
        for item in self.parameters:
            res.append(item.__repr__(indent + 1))
        return "\n".join(res)


Markup = tuple[Optional[str], Optional[str]]


class Marker:
    """
    Base class to markup nodes during serialization.
    """

    # pylint: disable=unused-argument
    def serializeToken(self, token: Token, node: CDDLNode) -> str:
        """
        Serialize a Token.

        The function must handle whitespaces and comments that the Token
        contains.
        """
        return token.serialize()

    # pylint: disable=unused-argument
    def serializeValue(self, prefix: str, value: str, suffix: str, node: Value) -> str:
        """
        Serialize a Value.
        """
        return prefix + value + suffix

    # pylint: disable=unused-argument
    def serializeName(self, name: str, node: Typename) -> str:
        """
        Serialize a typename or a groupname
        """
        return name

    # pylint: disable=unused-argument
    def markupFor(self, node: CDDLNode) -> Markup:
        """
        Wrapping markup for a node as a whole if needed
        """
        return (None, None)
