from pprint import pprint
import json
import re
from typing import cast, get_args

from .lexer import Lexer
from .tokens import Token, Tokens
from .ast import CDDLNode, CDDLTree, Rule, GroupEntry, Group, GroupChoice, \
    Array, Type, Type1, Type2, Typename, Value, Operator, Tag, Range, \
    Memberkey, Reference, Occurrence, OperatorName, \
    GenericParameters, GenericArguments

from math import inf

NIL_TOKEN: Token = Token(Tokens.ILLEGAL, '')
DEFAULT_OCCURRENCE: Occurrence = Occurrence(1, 1) # exactly one time

class Parser:
    l: Lexer
    curToken: Token = NIL_TOKEN
    peekToken: Token = NIL_TOKEN

    def __init__(self, source: str) -> None:
        self.l = Lexer(source)
        self._nextToken()
        self._nextToken()

    def parse(self) -> CDDLTree:
        rules: list[Rule] = []

        # cddl = S 1*(rule S)
        children: list[CDDLNode] = []

        while (self.curToken.type != Tokens.EOF):
            rule = self._parseRule()
            rules.append(rule)
            children.append(rule)

        # Add EOF token to the end of the tree so that serialization preserve
        # final whitespaces
        children.append(self._nextToken())
        tree = CDDLTree(rules)
        tree.children = children
        return tree

    def _parseRule(self) -> Rule:
        '''
        rule = typename [genericparm] S assignt S type
               / groupname [genericparm] S asssigng S grpent

        Both constructs are similar, we'll parse them the same way and merely
        distinguish in the end (without validating that the construct is
        correct)
        '''
        children: list[CDDLNode] = []

        # First thing we expect in a rule is a typename or a groupname
        typename = self._parseTypename(definition=True, unwrapped=False)
        children.append(typename)

        # Not much difference between "/=" and "//=", we'll treat them as
        # signaling choice additions
        isChoiceAddition = (
            self.curToken.type == Tokens.TCHOICEALT or
            self.curToken.type == Tokens.GCHOICEALT
        )
        if not (self.curToken.type == Tokens.ASSIGN or
                self.curToken.type == Tokens.TCHOICEALT or
                self.curToken.type == Tokens.GCHOICEALT):
            raise self._parserError(f'assignment expected, received "{self.curToken.str()}"')
        children.append(self._nextToken())

        groupEntry = self._parseGroupEntry()
        children.append(groupEntry)
        node = Rule(typename, isChoiceAddition, groupEntry)
        node.children = children
        return node

    def _parseGroupEntry(self) -> GroupEntry:
        '''
        grpent = [occur S] [memberkey S] type
               / [occur S] groupname [genericarg]  ; preempted by above
               / [occur S] "(" S group S ")"

        The function can also be used to parse a type
        '''
        children: list[CDDLNode] = []

        occurrence = self._parseOccurrence()
        if occurrence is None:
            occurrence = DEFAULT_OCCURRENCE
        else:
            children.append(occurrence)

        # memberkey is essentially a type followed by some specific tokens
        # (such as "=>" or ":"). We'll parse next tokens as a "loose" type,
        # meaning either as a type, a memberkey, or the construct
        # "(" S group S )". Once we know what we have, we know what're parsing.
        looseType = self._parseType(loose=True)
        children.append(looseType)
        if isinstance(looseType, Memberkey):
            type = self._parseType(loose=False)
            assert isinstance(type, Type)
            children.append(type)
            node = GroupEntry(occurrence, looseType, type)
        else:
            node = GroupEntry(occurrence, None, looseType)
        node.children = children
        return node

    def _parseType(self, loose: bool = False) -> Type | Memberkey:
        '''
        type = type1 *(S "/" S type1)

        If the "loose" flag is on, function also parses constructs that are
        used in grpent:
        memberkey = type1 S ["^" S] "=>"
                  / bareword S ":"
                  / value S ":"
        wrapped = "(" S group S ")"
        '''
        children: list[CDDLNode] = []

        altTypes: list[Type1] = []
        type1 = self._parseType1(loose)
        altTypes.append(type1)
        children.append(type1)

        if loose and self.curToken.type == Tokens.CARET:
            children.append(self._nextToken())
            if self.curToken.type != Tokens.ARROWMAP:
                raise self._parserError(f'expected arrow map, received "{self.curToken.str()}{self.peekToken.str()}"')
            children.append(self._nextToken())
            key = Memberkey(type1, hasCut=True)
            key.children = children
            return key
        elif loose and self.curToken.type == Tokens.ARROWMAP:
            children.append(self._nextToken())
            key = Memberkey(type1, hasCut=False)
            key.children = children
            return key
        elif loose and self.curToken.type == Tokens.COLON:
            children.append(self._nextToken())
            key = Memberkey(type1, hasCut=True)
            key.children = children
            return key

        while self.curToken.type == Tokens.TCHOICE:
            children.append(self._nextToken())
            altType = self._parseType1()
            altTypes.append(altType)
            children.append(altType)

        node = Type(altTypes)
        node.children = children
        return node

    def _parseType1(self, loose: bool = False) -> Type1:
        '''
        type1 = type2 [S (rangeop / ctlop) S type2]

        If the "loose" flag is on, function also parses an extended type2
        definition that also allows: "(" S group S ")"

        From an AST perspective, Type1 = Type2 | Range | Operator
        '''
        children: list[CDDLNode] = []
        type2 = self._parseType2(loose)
        children.append(type2)
        node: Type1
        if (self.curToken.type == Tokens.INCLRANGE or
                self.curToken.type == Tokens.EXCLRANGE):
            children.append(self._nextToken())
            inclusive = self.curToken.type == Tokens.INCLRANGE
            maxType = self._parseType2()
            children.append(maxType)
            # TODO: raise an error instead
            assert isinstance(type2, Value) or isinstance(type2, Typename)
            assert isinstance(maxType, Value) or isinstance(maxType, Typename)
            node = Range(type2, maxType, inclusive)
            node.children = children
        elif self.curToken.type == Tokens.CTLOP:
            assert self.curToken.literal in get_args(OperatorName)
            operatorName = cast(OperatorName, self.curToken.literal)
            children.append(self._nextToken())
            controlType = self._parseType2()
            children.append(controlType)
            node = Operator(type2, operatorName, controlType)
            node.children = children
        else:
            node = type2

        return node

    def _parseType2(self, loose: bool = False) -> Type2:
        '''
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
        '''
        children: list[CDDLNode] = []
        node: Type2
        match self.curToken.type:
            case Tokens.LPAREN:
                children.append(self._nextToken())
                if loose:
                    node = self._parseGroup(isMap=False)
                    # TODO: convert group back to a type if possible
                    children.extend(node.children)
                else:
                    type = self._parseType()
                    children.append(type)
                    # TODO: better class to represent a type wrapped in parentheses?
                    assert isinstance(type, Type)
                    groupEntry = GroupEntry(DEFAULT_OCCURRENCE, None, type)
                    groupChoice = GroupChoice([groupEntry])
                    node = Group([groupChoice], isMap=False)
                if self.curToken.type != Tokens.RPAREN:
                    raise self._parserError(f'expected right parenthesis, received "{self.curToken.str()}"')
                children.append(self._nextToken())

            case Tokens.LBRACE:
                children.append(self._nextToken())
                node = self._parseGroup(isMap=True)
                children.extend(node.children)
                if self.curToken.type != Tokens.RBRACE:
                    raise self._parserError(f'expected right brace, received "{self.curToken.str()}"')
                children.append(self._nextToken())

            case Tokens.LBRACK:
                children.append(self._nextToken())
                group = self._parseGroup(isMap=False)
                children.extend(group.children)
                node = Array(group.groupChoices)
                if self.curToken.type != Tokens.RBRACK:
                    raise self._parserError(f'expected right bracket, received "{self.curToken.str()}"')
                children.append(self._nextToken())

            case Tokens.TILDE:
                children.append(self._nextToken())
                node = self._parseTypename(definition=False, unwrapped=True)
                children.extend(node.children)

            case Tokens.AMPERSAND:
                children.append(self._nextToken())
                if self.curToken.type == Tokens.LPAREN:
                    children.append(self._nextToken())
                    group = self._parseGroup(isMap=False)
                    node = Reference(group)
                    children.append(group)
                    if self.curToken.type != Tokens.RPAREN:
                        raise self._parserError(f'expected right parenthesis, received "{self.curToken.str()}"')
                    children.append(self._nextToken())
                else:
                    typename = self._parseTypename(definition=False, unwrapped=False)
                    children.append(typename)
                    node = Reference(typename)

            case Tokens.HASH:
                children.append(self._nextToken())
                if self.curToken.type == Tokens.NUMBER or self.curToken.type == Tokens.FLOAT:
                    number = self._nextToken()
                    children.append(number)
                    if number.literal[0] == '6' and self.curToken.type == Tokens.LPAREN:
                        children.append(self._nextToken())
                        type = self._parseType()
                        children.append(type)
                        if self.curToken.type != Tokens.RPAREN:
                            raise self._parserError(f'expected right parenthesis, received "{self.curToken.str()}"')
                        children.append(self._nextToken())
                        node = Tag(number, type)
                    else:
                        node = Tag(number)
                else:
                    node = Tag()

            case Tokens.IDENT:
                node = self._parseTypename(definition=False, unwrapped=False)
                children = node.children

            case Tokens.STRING:
                value = self._nextToken()
                children.append(value)
                node = Value(value.literal, 'text')

            case Tokens.BYTES:
                value = self._nextToken()
                children.append(value)
                node = Value(value.literal, 'bytes')

            case Tokens.HEX:
                value = self._nextToken()
                children.append(value)
                node = Value(value.literal, 'hex')

            case Tokens.BASE64:
                value = self._nextToken()
                children.append(value)
                node = Value(value.literal, 'base64')

            case Tokens.NUMBER:
                value = self._nextToken()
                children.append(value)
                node = Value(value.literal, 'number')

            case Tokens.FLOAT:
                value = self._nextToken()
                children.append(value)
                node = Value(value.literal, 'number')

            case _:
                raise self._parserError(f'invalid type2 production, received "{self.curToken.str()}"')

        node.children = children
        return node

    def _parseGroup(self, isMap: bool = False) -> Group:
        '''
        group = grpchoice *(S "//" S grpchoice)
        grpchoice = *(grpent optcom)
        optcom = S ["," S]

        A group construct may be empty, but since it can only appear enclosed
        in parentheses, braces or brackets, it's easy to know when to stop.
        '''
        children: list[CDDLNode] = []

        groupChoices: list[GroupChoice] = []
        groupEntries: list[GroupEntry] = []
        while True:
            if (self.curToken.type == Tokens.RPAREN or
                self.curToken.type == Tokens.RBRACE or
                self.curToken.type == Tokens.RBRACK):
                break
            while not self.curToken.type == Tokens.GCHOICE:
                groupEntry = self._parseGroupEntry()
                groupEntries.append(groupEntry)
                children.append(groupEntry)
                if self.curToken.type == Tokens.COMMA:
                    children.append(self._nextToken())
                if (self.curToken.type == Tokens.RPAREN or
                    self.curToken.type == Tokens.RBRACE or
                    self.curToken.type == Tokens.RBRACK):
                    break
            groupChoices.append(GroupChoice(groupEntries))
            if (self.curToken.type == Tokens.RPAREN or
                self.curToken.type == Tokens.RBRACE or
                self.curToken.type == Tokens.RBRACK):
                break
            children.append(self._nextToken())

        node = Group(groupChoices, isMap)
        node.children = children
        return node

    def _parseOccurrence(self) -> Occurrence | None:
        children: list[CDDLNode] = []
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
        if self.curToken.type == Tokens.QUEST or self.curToken.type == Tokens.ASTERISK or self.curToken.type == Tokens.PLUS:
            n = 1 if self.curToken.type == Tokens.PLUS else 0
            m = inf

            # check if there is a max definition
            # (that max definition MUST be right after the asterisk, if there's a space
            # the number is an identifier, not a max definition!)
            if (self.curToken.type == Tokens.ASTERISK and
                self.peekToken.type == Tokens.NUMBER and
                self.peekToken.whitespace == ''):
                m = int(self.peekToken.literal)
                children.append(self._nextToken())

            occurrence = Occurrence(n, m)
            children.append(self._nextToken())
        # numbered occurrence indicator, e.g.
        # ```
        #  1*10 bedroom: size,
        # ```
        elif (
            self.curToken.type == Tokens.NUMBER and
            self.peekToken.type == Tokens.ASTERISK
        ):
            n = int(self.curToken.literal)
            m = inf
            children.append(self._nextToken()) # eat "n"
            children.append(self._nextToken()) # eat "*"

            # check if there is a max definition
            if self.curToken.type == Tokens.NUMBER:
                m = int(self.curToken.literal)
                children.append(self._nextToken())

            occurrence = Occurrence(n, m)

        if occurrence is not None:
            occurrence.children = children
        return occurrence

    def _parseIdentifier(self) -> Token:
        if self.curToken.type != Tokens.IDENT:
            raise self._parserError(f'group identifier expected, received "{self.curToken.str()}"')
        name = self.curToken
        self._nextToken()
        return name

    def _parseTypename(self, definition: bool = False, unwrapped: bool = False) -> Typename:
        ident = self._parseIdentifier()
        parameters: GenericParameters | GenericArguments | None
        if definition:
            parameters = self._parseGenericParameters()
        else:
            parameters = self._parseGenericArguments()
        typename = Typename(ident.literal, unwrapped, parameters)
        typename.children.append(ident)
        if parameters is not None:
            typename.children.append(parameters)
        return typename

    def _parseGenericParameters(self) -> GenericParameters | None:
        '''
        genericparm = "<" S id S *("," S id S ) ">"
        '''
        if self.curToken.type != Tokens.LT:
            return None
        children: list[CDDLNode] = []
        children.append(self._nextToken())

        parameters: list[str] = []
        name = self._parseIdentifier()
        parameters.append(name.literal)
        children.append(name)
        while self.curToken.type == Tokens.COMMA:
            children.append(self._nextToken())
            name = self._parseIdentifier()
            parameters.append(name.literal)
            children.append(name)
        if self.curToken.type != Tokens.GT:
            raise self._parserError(f'">" character expected to end generic production, received "{self.curToken.str()}"')
        children.append(self._nextToken())

        node = GenericParameters(parameters)
        node.children = children
        return node

    def _parseGenericArguments(self) -> GenericArguments | None:
        '''
        genericarg = "<" S type1 S *("," S type1 S ) ">"

        The function is very similar to the _parseGenericParameters function
        expect that type1 replaces id
        '''
        if self.curToken.type != Tokens.LT:
            return None
        children: list[CDDLNode] = []
        children.append(self._nextToken())

        parameters: list[Type1] = []
        type1 = self._parseType1()
        parameters.append(type1)
        children.append(type1)
        while self.curToken.type == Tokens.COMMA:
            children.append(self._nextToken())
            type1 = self._parseType1()
            parameters.append(type1)
            children.append(type1)
        if self.curToken.type != Tokens.GT:
            raise self._parserError(f'">" character expected to end generic production, received "{self.curToken.str()}"')
        children.append(self._nextToken())

        node = GenericArguments(parameters)
        node.children = children
        return node

    def _nextToken(self) -> Token:
        curToken = self.curToken
        self.curToken = self.peekToken
        self.peekToken = self.l.nextToken()
        return curToken

    def _parserError(self, message: str) -> Exception:
        location = self.l.getLocation()
        locInfo = self.l.getLocationInfo()
        return Exception(f'{location.line + 1}:{location.position} - error: {message}\n\n{locInfo}')
