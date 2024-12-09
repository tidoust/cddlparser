from typing import get_args
from math import inf

from .errors import ParserError
from .lexer import Lexer
from .tokens import Token, Tokens
from .utils import isUint
from .ast import (
    CDDLTree,
    CDDLNode,
    Rule,
    GroupEntry,
    Group,
    Map,
    Array,
    GroupChoice,
    Type,
    Type1,
    Type2,
    Typename,
    Value,
    Operator,
    Tag,
    Range,
    Memberkey,
    ChoiceFrom,
    Occurrence,
    OperatorName,
    GenericParameters,
    GenericArguments,
    PreludeType,
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
        tree.setChildrenParent()

        # Some of the rules are type definitions, but we can only know for sure
        # when the whole CDDL has been parsed. Convert GroupEntry instances to
        # Type where appropriate
        self._convertGroupDefinitions(tree)

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

        # If "=" is used, there's no way to tell directly whether the construct
        # is a group or type definition. We'll default to a group.
        assign = self._nextToken()
        if assign.type in (Tokens.ASSIGN, Tokens.GCHOICEALT):
            groupEntry = self._parseGroupEntry()
            node = Rule(typename, assign, groupEntry)
        elif assign.type == Tokens.TCHOICEALT:
            ruleType = self._parseType()
            assert isinstance(ruleType, Type)
            node = Rule(typename, assign, ruleType)
        else:
            raise self._parserError(
                f'assignment expected, received "{assign.serialize()}"'
            )
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
        # "(" S group S )".
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
            if not isinstance(type2, (Value, Typename)):
                raise self._parserError(
                    f"range detected but min is neither a value nor a typename. Got: {type2.serialize()}"
                )
            if not isinstance(maxType, (Value, Typename)):
                raise self._parserError(
                    f"range detected but max is neither a value nor a typename. Got: {maxType.serialize()}"
                )
            node = Range(type2, maxType, rangeop)
        elif self.curToken.type == Tokens.CTLOP:
            if self.curToken.literal not in get_args(OperatorName):
                raise self._parserError(
                    f'unknown control operator "{self.curToken.literal}"'
                )
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
                else:
                    innerType = self._parseType()
                    assert isinstance(innerType, Type)
                    node = innerType
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
                    node = ChoiceFrom(group)
                else:
                    typename = self._parseTypename(definition=False, unwrapped=None)
                    node = ChoiceFrom(typename)
                node.setComments(refToken)

            case Tokens.HASH:
                hashToken = self._nextToken()
                if (
                    self.curToken.type in {Tokens.NUMBER, Tokens.FLOAT}
                    and not self.curToken.startWithSpaces()
                ):
                    number = self._nextToken()
                    if len(number.literal) > 1 and (
                        number.literal[1] != "." or "e" in number.literal
                    ):
                        raise self._parserError(
                            f'data item after "#" must match DIGIT ["." uint], got "{self.curToken.serialize()}"'
                        )
                    if (
                        number.literal[0] == "6"
                        and self.curToken.type == Tokens.LPAREN
                        and not self.curToken.startWithSpaces()
                    ):
                        type2 = self._parseType2()
                        assert isinstance(type2, Type)
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

        node: Map | Group
        if isMap:
            node = Map(groupChoices)
        else:
            node = Group(groupChoices)
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
            # (that max definition MUST be right after the asterisk, if there's a space, the number is an identifier, not a max definition!)
            if (
                self.curToken.type == Tokens.ASTERISK
                and self.peekToken.type == Tokens.NUMBER
                and isUint(self.peekToken.literal)
                and not self.peekToken.startWithSpaces()
            ):
                tokens.append(self._nextToken())
                m = int(self.curToken.literal)

            tokens.append(self._nextToken())
            occurrence = Occurrence(n, m, tokens)
        # numbered occurrence indicator, e.g.
        # ```
        #  1*10 bedroom: size,
        # ```
        elif (
            self.curToken.type == Tokens.NUMBER
            and isUint(self.curToken.literal)
            and self.peekToken.type == Tokens.ASTERISK
            and not self.peekToken.startWithSpaces()
        ):
            n = int(self.curToken.literal)
            m = inf
            tokens.append(self._nextToken())  # eat "n"
            tokens.append(self._nextToken())  # eat "*"

            # check if there is a max definition
            if (
                self.curToken.type == Tokens.NUMBER
                and isUint(self.curToken.literal)
                and not self.curToken.startWithSpaces()
            ):
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
        if self.curToken.type != Tokens.LT or self.curToken.startWithSpaces():
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
        if self.curToken.type != Tokens.LT or self.curToken.startWithSpaces():
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

    def _convertGroupDefinitions(self, tree: CDDLTree) -> None:
        """
        The parser creates a tree where the right-hand side of all rules are a
        GroupEntry. Sometimes, we really know that we're dealing with a type
        definition and not a group definition. This method converts GroupEntry
        instances to Type instances when possible.

        Note it is not always possible to determine whether a definition is a
        type definition or a group definition. Also, the logic is likely
        slightly incomplete. Whenever in doubt, this method keeps the initial
        GroupEntry instance.
        """
        rulenames: set[str] = set()
        typenames: set[str] = set()
        groupnames: set[str] = set()

        def checkUnderlyingType(type1: Type1) -> str:
            """
            Check the underlying type of the given type1 variable.

            A Value, a Map, an Array, a ChoiceFrom, or a Tag signal a type.
            A prelude type signals a type as well.

            For other typenames, that depends.
            """
            if isinstance(type1, (Value, Map, Array, ChoiceFrom, Tag)):
                return "type"
            if isinstance(type1, Range):
                return checkUnderlyingType(type1.min)
            if isinstance(type1, Operator):
                return checkUnderlyingType(type1.type)
            if isinstance(type1, Typename):
                name = type1.name
                if name in typenames or name in get_args(PreludeType):
                    return "type"
                if name in groupnames:
                    return "group"
            return "unknown"

        # First pass to determine rules that obviously must be a type or group
        # definitions.
        for rule in tree.rules:
            rulenames.add(rule.name.name)

            # First rule is always a type:
            # https://datatracker.ietf.org/doc/html/rfc8610#section-2.2.4
            # (note we're going to check the rule further, since it could be
            # incorrectly defined as a group too)
            if len(typenames) == 0:
                typenames.add(rule.name.name)

            # If parser created a Type (typically because "/=" was used),
            # we already know it's a type
            if isinstance(rule.type, Type):
                typenames.add(rule.name.name)
                continue
            assert isinstance(rule.type, GroupEntry)

            # Use of "/=" explicitly signals a typename
            # (note: checked here in case someone assembles a tree on their
            # own, but the parser already generated a Type)
            if rule.assign.type == Tokens.TCHOICEALT:
                typenames.add(rule.name.name)

            # Use of "//=" explicitly signals a groupname
            if rule.assign.type == Tokens.GCHOICEALT:
                groupnames.add(rule.name.name)

            # If there are alternate choices not wrapped in parentheses,
            # that's a type
            if len(rule.type.type.types) > 1 and rule.type.type.openToken is None:
                typenames.add(rule.name.name)

            # If entry defines an occurrence or a key, that's a group
            if rule.type.occurrence is not None:
                groupnames.add(rule.name.name)
            if rule.type.key is not None:
                groupnames.add(rule.name.name)

        # Recursive check in the tree to look for typenames that are used as
        # group keys (real typenames, not barewords). Such keys are types, see:
        # https://datatracker.ietf.org/doc/html/rfc8610#section-2.1.2
        def lookForKeys(node: CDDLNode):
            if (
                isinstance(node, GroupEntry)
                and node.key is not None
                and isinstance(node.key.type, Typename)
                and not node.key.hasColon
                and node.key.type.name in rulenames
            ):
                typenames.add(node.key.type.name)
            for child in node.getChildren():
                lookForKeys(child)

        lookForKeys(tree)

        # Rule definitions that directly reference a prelude type, a tag or a
        # value are type definitions.
        # Rule definitions that directly reference a rule that we know is a
        # type (resp. group) definition are type (resp. group) definitions too.
        # Rules referenced by a rule that is a type (resp. group) definition are
        # type (resp. group) definitions too.
        # Rule definitions that reference a mix of type and group rules are
        # invalid.
        updateFound = True
        while updateFound:
            updateFound = False
            for rule in tree.rules:
                if isinstance(rule.type, Type):
                    for type1 in rule.type.types:
                        if isinstance(type1, Typename) and type1.name in rulenames:
                            updateFound = type1.name not in typenames
                            typenames.add(type1.name)
                    continue
                assert isinstance(rule.type, GroupEntry)
                if rule.name.name in typenames:
                    for type1 in rule.type.type.types:
                        if isinstance(type1, Typename) and type1.name in rulenames:
                            updateFound = type1.name not in typenames
                            typenames.add(type1.name)
                if rule.name.name in groupnames:
                    # Note: there should be one and only one type1 in
                    # rule.type.type.types in practice.
                    for type1 in rule.type.type.types:
                        if isinstance(type1, Typename) and type1.name in rulenames:
                            updateFound = type1.name not in groupnames
                            groupnames.add(type1.name)
                if rule.assign.type == Tokens.ASSIGN:
                    defTypes: set[str] = {
                        checkUnderlyingType(type1) for type1 in rule.type.type.types
                    }
                    if "type" in defTypes and "group" in defTypes:
                        raise self._parserError(
                            f'rule "{rule.name.name}" targets a mix of type and group rules'
                        )
                    if "type" in defTypes:
                        updateFound = rule.name.name not in typenames
                        typenames.add(rule.name.name)
                    elif "group" in defTypes:
                        updateFound = rule.name.name not in groupnames
                        groupnames.add(rule.name.name)

        # There should be no overlap between the two lists
        overlap = list(set(typenames) & set(groupnames))
        if len(overlap) > 0:
            overlapStr = ", ".join(overlap)
            raise self._parserError(
                f"mix of type and group definitions for {overlapStr}"
            )

        # Convert GroupEntry to Type for type definitions
        for rule in tree.rules:
            if isinstance(rule.type, Type):
                continue
            assert isinstance(rule.type, GroupEntry)
            if rule.name.name in typenames:
                if not rule.type.isConvertibleToType():
                    raise self._parserError(
                        f'rule "{rule.name.name}" is a type definition but uses a group entry'
                    )
                rule.type = rule.type.type

    def _nextToken(self) -> Token:
        curToken = self.curToken
        self.curToken = self.peekToken
        self.peekToken = self.lexer.nextToken()
        return curToken

    def _parserError(self, message: str) -> ParserError:
        location = self.lexer.getLocation()
        locInfo = self.lexer.getLocationInfo()
        return ParserError(
            f"CDDL syntax error - line {location.line + 1}, col {location.position}: {message}\n\n{locInfo}"
        )
