# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
# pylint: disable=invalid-name, fixme, too-many-statements, too-few-public-methods
# pylint: disable=line-too-long

from typing import get_args
from math import inf

from .lexer import Lexer
from .tokens import Token, Tokens
from .ast import (
    CDDLTree,
    Rule,
    GroupEntry,
    Group,
    GroupChoice,
    Array,
    Type,
    Type1,
    Type2,
    Typename,
    Value,
    Operator,
    Tag,
    Range,
    Memberkey,
    Reference,
    Occurrence,
    OperatorName,
    GenericParameters,
    GenericArguments,
)

NIL_TOKEN: Token = Token(Tokens.ILLEGAL, "")


class Parser:
    lexer: Lexer
    curToken: Token = NIL_TOKEN
    peekToken: Token = NIL_TOKEN

    def __init__(self, source: str) -> None:
        self.lexer = Lexer(source)
        self._nextToken()
        self._nextToken()

    def parse(self) -> CDDLTree:
        # cddl = S 1*(rule S)
        rules: list[Rule] = []

        while self.curToken.type != Tokens.EOF:
            rule = self._parseRule()
            rules.append(rule)

        # Add EOF token to the end of the tree so that serialization preserve
        # final whitespaces
        tree = CDDLTree(rules)
        tree.separator = self._nextToken()
        return tree

    def _parseRule(self) -> Rule:
        """
        rule = typename [genericparm] S assignt S type
               / groupname [genericparm] S asssigng S grpent

        Both constructs are similar, we'll parse them the same way and merely
        distinguish in the end (without validating that the construct is
        correct)
        """

        # First thing we expect in a rule is a typename or a groupname
        typename = self._parseTypename(definition=True, unwrapped=None)

        # Not much difference between "/=" and "//=", we'll treat them as
        # signaling choice additions
        assign = self._nextToken()
        if assign.type not in (Tokens.ASSIGN, Tokens.TCHOICEALT, Tokens.GCHOICEALT):
            raise self._parserError(
                f'assignment expected, received "{assign.serialize()}"'
            )

        # TODO: convert GroupEntry back to a Type if possible or needed
        # because "//=" was used
        groupEntry = self._parseGroupEntry()
        node = Rule(typename, assign, groupEntry)
        return node

    def _parseGroupEntry(self) -> GroupEntry:
        """
        grpent = [occur S] [memberkey S] type
               / [occur S] groupname [genericarg]  ; preempted by above
               / [occur S] "(" S group S ")"

        The function can also be used to parse a type
        """
        occurrence = self._parseOccurrence()

        # memberkey is essentially a type followed by some specific tokens
        # (such as "=>" or ":"). We'll parse next tokens as a "loose" type,
        # meaning either as a type, a memberkey, or the construct
        # "(" S group S )". Once we know what we have, we know what're parsing.
        looseType = self._parseType(loose=True)
        if isinstance(looseType, Memberkey):
            entryType = self._parseType(loose=False)
            assert isinstance(entryType, Type)
            node = GroupEntry(occurrence, looseType, entryType)
        else:
            node = GroupEntry(occurrence, None, looseType)
        return node

    def _parseType(self, loose: bool = False) -> Type | Memberkey:
        """
        type = type1 *(S "/" S type1)

        If the "loose" flag is on, function also parses constructs that are
        used in grpent:
        memberkey = type1 S ["^" S] "=>"
                  / bareword S ":"
                  / value S ":"
        wrapped = "(" S group S ")"
        """
        altTypes: list[Type1] = []
        type1 = self._parseType1(loose)
        altTypes.append(type1)

        if loose and self.curToken.type == Tokens.CARET:
            caretTokens: list[Token] = []
            caretTokens.append(self._nextToken())
            if self.curToken.type != Tokens.ARROWMAP:
                raise self._parserError(
                    f'expected arrow map, received "{self.curToken.serialize()}{self.peekToken.serialize()}"'
                )
            caretTokens.append(self._nextToken())
            key = Memberkey(type1, hasCut=True, hasColon=False, tokens=caretTokens)
            return key
        if loose and self.curToken.type == Tokens.ARROWMAP:
            key = Memberkey(
                type1, hasCut=False, hasColon=False, tokens=[self._nextToken()]
            )
            return key
        if loose and self.curToken.type == Tokens.COLON:
            key = Memberkey(
                type1, hasCut=True, hasColon=True, tokens=[self._nextToken()]
            )
            return key

        while self.curToken.type == Tokens.TCHOICE:
            # Record the separator with the previous type
            type1.separator = self._nextToken()
            type1 = self._parseType1()
            altTypes.append(type1)

        node = Type(altTypes)
        return node

    def _parseType1(self, loose: bool = False) -> Type1:
        """
        type1 = type2 [S (rangeop / ctlop) S type2]

        If the "loose" flag is on, function also parses an extended type2
        definition that also allows: "(" S group S ")"

        From an AST perspective, Type1 = Type2 | Range | Operator
        """
        type2 = self._parseType2(loose)
        node: Type1
        if self.curToken.type in (Tokens.INCLRANGE, Tokens.EXCLRANGE):
            rangeop = self._nextToken()
            maxType = self._parseType2()
            # TODO: raise an error instead
            assert isinstance(type2, (Value, Typename))
            assert isinstance(maxType, (Value, Typename))
            node = Range(type2, maxType, rangeop)
        elif self.curToken.type == Tokens.CTLOP:
            assert self.curToken.literal in get_args(OperatorName)
            operator = self._nextToken()
            controlType = self._parseType2()
            node = Operator(type2, operator, controlType)
        else:
            node = type2

        return node

    def _parseType2(self, loose: bool = False) -> Type2:
        """
        type2 = value
              / typename [genericarg]
              / "(" S type S ")"
              / "{" S group S "}"
              / "[" S group S "]"
              / "~" S typename [genericarg]
              / "&" S "(" S group S ")"
              / "&" S groupname [genericarg]
              / "#" "6" ["." uint] "(" S type S ")"
              / "#" DIGIT ["." uint]                ; major/ai
              / "#"                                 ; any

        If the loose flag is set, the function also parses the alternative
        used in grpent:
              / "(" S group S ")"
        """
        node: Type2
        match self.curToken.type:
            case Tokens.LPAREN:
                openToken = self._nextToken()
                if loose:
                    node = self._parseGroup(isMap=False)
                    node.openToken = openToken
                else:
                    wrappedType = self._parseType()
                    # TODO: better class to represent a type wrapped in parentheses?
                    assert isinstance(wrappedType, Type)
                    groupEntry = GroupEntry(None, None, wrappedType)
                    groupChoice = GroupChoice([groupEntry])
                    node = Group([groupChoice], isMap=False)
                    node.openToken = openToken
                if self.curToken.type != Tokens.RPAREN:
                    raise self._parserError(
                        f'expected right parenthesis, received "{self.curToken.serialize()}"'
                    )
                node.closeToken = self._nextToken()

            case Tokens.LBRACE:
                openToken = self._nextToken()
                node = self._parseGroup(isMap=True)
                node.openToken = openToken
                if self.curToken.type != Tokens.RBRACE:
                    raise self._parserError(
                        f'expected right brace, received "{self.curToken.serialize()}"'
                    )
                node.closeToken = self._nextToken()

            case Tokens.LBRACK:
                openToken = self._nextToken()
                group = self._parseGroup(isMap=False)
                node = Array(group.groupChoices)
                node.openToken = openToken
                if self.curToken.type != Tokens.RBRACK:
                    raise self._parserError(
                        f'expected right bracket, received "{self.curToken.serialize()}"'
                    )
                node.closeToken = self._nextToken()

            case Tokens.TILDE:
                unwrapped = self._nextToken()
                node = self._parseTypename(definition=False, unwrapped=unwrapped)

            case Tokens.AMPERSAND:
                refToken = self._nextToken()
                if self.curToken.type == Tokens.LPAREN:
                    openToken = self._nextToken()
                    group = self._parseGroup(isMap=False)
                    group.openToken = openToken
                    if self.curToken.type != Tokens.RPAREN:
                        raise self._parserError(
                            f'expected right parenthesis, received "{self.curToken.serialize()}"'
                        )
                    group.closeToken = self._nextToken()
                    node = Reference(group)
                else:
                    typename = self._parseTypename(definition=False, unwrapped=None)
                    node = Reference(typename)
                node.setComments(refToken)

            case Tokens.HASH:
                hashToken = self._nextToken()
                if self.curToken.type in {Tokens.NUMBER, Tokens.FLOAT}:
                    number = self._nextToken()
                    if number.literal[0] == "6" and self.curToken.type == Tokens.LPAREN:
                        # TODO: assert that there is no space between number and "("
                        type2 = self._parseType2()
                        # TODO: raise an error instead
                        assert isinstance(type2, Group)
                        assert len(type2.groupChoices) == 1
                        assert len(type2.groupChoices[0].groupEntries) == 1
                        assert isinstance(
                            type2.groupChoices[0].groupEntries[0].type, Type
                        )
                        node = Tag(number, type2)
                    else:
                        node = Tag(number)
                else:
                    node = Tag()
                node.setComments(hashToken)

            case Tokens.IDENT:
                node = self._parseTypename(definition=False, unwrapped=None)

            case Tokens.STRING:
                value = self._nextToken()
                node = Value(value.literal, "text")
                node.setComments(value)

            case Tokens.BYTES:
                value = self._nextToken()
                node = Value(value.literal, "bytes")
                node.setComments(value)

            case Tokens.HEX:
                value = self._nextToken()
                node = Value(value.literal, "hex")
                node.setComments(value)

            case Tokens.BASE64:
                value = self._nextToken()
                node = Value(value.literal, "base64")
                node.setComments(value)

            case Tokens.NUMBER:
                value = self._nextToken()
                node = Value(value.literal, "number")
                node.setComments(value)

            case Tokens.FLOAT:
                value = self._nextToken()
                node = Value(value.literal, "number")
                node.setComments(value)

            case _:
                raise self._parserError(
                    f'invalid type2 production, received "{self.curToken.serialize()}"'
                )

        return node

    def _parseGroup(self, isMap: bool = False) -> Group:
        """
        group = grpchoice *(S "//" S grpchoice)
        grpchoice = *(grpent optcom)
        optcom = S ["," S]

        A group construct may be empty, but since it can only appear enclosed
        in parentheses, braces or brackets, it's easy to know when to stop.
        """
        groupChoices: list[GroupChoice] = []
        while True:
            if self.curToken.type in (Tokens.RPAREN, Tokens.RBRACE, Tokens.RBRACK):
                break
            groupEntries: list[GroupEntry] = []
            while self.curToken.type != Tokens.GCHOICE:
                groupEntry = self._parseGroupEntry()
                groupEntries.append(groupEntry)
                if self.curToken.type == Tokens.COMMA:
                    groupEntry.separator = self._nextToken()
                if self.curToken.type in (Tokens.RPAREN, Tokens.RBRACE, Tokens.RBRACK):
                    break
            groupChoice = GroupChoice(groupEntries)
            groupChoices.append(groupChoice)
            if self.curToken.type in (Tokens.RPAREN, Tokens.RBRACE, Tokens.RBRACK):
                break
            groupChoice.separator = self._nextToken()

        node = Group(groupChoices, isMap)
        return node

    def _parseOccurrence(self) -> Occurrence | None:
        tokens: list[Token] = []
        occurrence: Occurrence | None = None

        # check for non-numbered occurrence indicator, e.g.
        # ```
        #  * bedroom: size,
        # ```
        # which is the same as:
        # ```
        #  ? bedroom: size,
        # ```
        # or have miniumum of 1 occurrence
        # ```
        #  + bedroom: size,
        # ```
        if self.curToken.type in {Tokens.QUEST, Tokens.ASTERISK, Tokens.PLUS}:
            n = 1 if self.curToken.type == Tokens.PLUS else 0
            m = inf

            # check if there is a max definition
            # (that max definition MUST be right after the asterisk, if there's a space
            # the number is an identifier, not a max definition!)
            if (
                self.curToken.type == Tokens.ASTERISK
                and self.peekToken.type == Tokens.NUMBER
                and self.peekToken.whitespace == ""
            ):
                m = int(self.peekToken.literal)
                tokens.append(self._nextToken())

            tokens.append(self._nextToken())
            occurrence = Occurrence(n, m, tokens)
        # numbered occurrence indicator, e.g.
        # ```
        #  1*10 bedroom: size,
        # ```
        elif (
            self.curToken.type == Tokens.NUMBER
            and self.peekToken.type == Tokens.ASTERISK
        ):
            # TODO: assert no space between min number and ASTERISK
            n = int(self.curToken.literal)
            m = inf
            tokens.append(self._nextToken())  # eat "n"
            tokens.append(self._nextToken())  # eat "*"

            # check if there is a max definition
            if self.curToken.type == Tokens.NUMBER:
                # TODO: assert no space between ASTERISK and max number
                m = int(self.curToken.literal)
                tokens.append(self._nextToken())

            occurrence = Occurrence(n, m, tokens)

        return occurrence

    def _parseTypename(
        self, definition: bool = False, unwrapped: Token | None = None
    ) -> Typename:
        if self.curToken.type != Tokens.IDENT:
            raise self._parserError(
                f'group identifier expected, received "{self.curToken.serialize()}"'
            )
        ident = self._nextToken()
        parameters: GenericParameters | GenericArguments | None
        if definition:
            parameters = self._parseGenericParameters()
        else:
            parameters = self._parseGenericArguments()
        typename = Typename(ident.literal, unwrapped, parameters)
        typename.setComments(ident)
        return typename

    def _parseGenericParameters(self) -> GenericParameters | None:
        """
        genericparm = "<" S id S *("," S id S ) ">"
        """
        # TODO: make sure there is no space before "<"
        if self.curToken.type != Tokens.LT:
            return None
        openToken = self._nextToken()

        parameters: list[Typename] = []
        name = self._parseTypename()
        parameters.append(name)
        while self.curToken.type == Tokens.COMMA:
            name.separator = self._nextToken()
            name = self._parseTypename()
            parameters.append(name)

        node = GenericParameters(parameters)
        node.openToken = openToken
        if self.curToken.type != Tokens.GT:
            raise self._parserError(
                f'">" character expected to end generic production, received "{self.curToken.serialize()}"'
            )
        node.closeToken = self._nextToken()
        return node

    def _parseGenericArguments(self) -> GenericArguments | None:
        """
        genericarg = "<" S type1 S *("," S type1 S ) ">"

        The function is very similar to the _parseGenericParameters function
        expect that type1 replaces id
        """
        # TODO: make sure there is no space before "<"
        if self.curToken.type != Tokens.LT:
            return None
        openToken = self._nextToken()

        parameters: list[Type1] = []
        type1 = self._parseType1()
        parameters.append(type1)
        while self.curToken.type == Tokens.COMMA:
            type1.separator = self._nextToken()
            type1 = self._parseType1()
            parameters.append(type1)

        node = GenericArguments(parameters)
        node.openToken = openToken
        if self.curToken.type != Tokens.GT:
            raise self._parserError(
                f'">" character expected to end generic production, received "{self.curToken.serialize()}"'
            )
        node.closeToken = self._nextToken()
        return node

    def _nextToken(self) -> Token:
        curToken = self.curToken
        self.curToken = self.peekToken
        self.peekToken = self.lexer.nextToken()
        return curToken

    def _parserError(self, message: str) -> Exception:
        location = self.lexer.getLocation()
        locInfo = self.lexer.getLocationInfo()
        return Exception(
            f"CDDL SYNTAX ERROR - line {location.line + 1}, col {location.position}: {message}\n\n{locInfo}"
        )
