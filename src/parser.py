from pprint import pprint
import json
import re
from typing import Optional, cast

from .lexer import Lexer
from .tokens import Token, Tokens
from .constants import PREDEFINED_IDENTIFIER, BOOLEAN_LITERALS
from .utils import parseNumberValue
from .ast import Property, Type, PropertyName, PropertyType, PropertyReference, Variable, RangePropertyReference, Occurrence, Assignment, Comment, Group, Array, OperatorType, NativeTypeWithOperator, Operator, Tag, Range


from math import inf

NIL_TOKEN: Token = Token(Tokens.ILLEGAL, '')
DEFAULT_OCCURRENCE: Occurrence = Occurrence(1, 1) # exactly one time
OPERATORS: list[OperatorType] = ['default', 'size', 'regexp', 'bits', 'and', 'within', 'eq', 'ne', 'lt', 'le', 'gt', 'ge']
OPERATORS_EXPECTING_VALUES = {
    'default': None,
    'size': ['literal', 'range'],
    'regexp': ['literal'],
    'bits': ['group'],
    'and': ['group'],
    'within': ['group'],
    'eq': ['group'],
    'ne': ['group'],
    'lt': ['group'],
    'le': ['group'],
    'gt': ['group'],
    'ge': ['group'],
}

class Parser:
    l: Lexer
    curToken: Token = NIL_TOKEN
    peekToken: Token = NIL_TOKEN

    def __init__(self, source: str) -> None:
        self.l = Lexer(source)
        self._nextToken()
        self._nextToken()

    def _nextToken(self) -> bool:
        self.curToken = self.peekToken
        self.peekToken = self.l.nextToken()
        return True

    def _parseAssignments(self) -> Assignment:
        comments: list[Comment] = []
        while (self.curToken.type == Tokens.COMMENT):
            comment = self._parseComment()
            assert comment is not None
            comments.append(comment)

        # expect group identifier, e.g.
        # groupName =
        # groupName /=
        # groupName //=
        if (self.curToken.type != Tokens.IDENT or
                not (self.peekToken.type == Tokens.ASSIGN or
                    self.peekToken.type == Tokens.SLASH)):
            raise self._parserError(f'group identifier expected, received "{json.dumps(self.curToken)}"')

        isChoiceAddition = False
        groupName = self.curToken.literal
        self._nextToken() # eat group identifier

        if self.curToken.type == Tokens.SLASH:
            isChoiceAddition = True
            self._nextToken() # eat `/`

        if self.curToken.type == Tokens.SLASH:
            self._nextToken() # eat `/`

        self._nextToken() # eat `=`
        assignmentValue = self._parseAssignmentValue(groupName, isChoiceAddition)

        while (self.curToken.type == Tokens.COMMENT):
            comment = self._parseComment()
            if comment is not None:
                comments.append(comment)
        assert isinstance(assignmentValue, Assignment)
        assignmentValue.comments = comments
        return assignmentValue

    def _parseAssignmentValue(self, groupName: Optional[str] = None, isChoiceAddition: bool = False) -> Assignment | list[PropertyType]:
        isChoice = False
        valuesOrProperties: list[Property | list[Property]] = []
        closingTokens = self._openSegment()

        # if no group segment was opened we have a variable assignment
        # and can return immediatelly, e.g.
        #
        #   attire = "bow tie" / "necktie" / "Internet attire"
        #
        if len(closingTokens) == 0:
            if groupName is not None:
                variable = Variable(
                    groupName,
                    isChoiceAddition,
                    self._parsePropertyTypes(),
                    comments = []
                )
                return variable
            return self._parsePropertyTypes()

        
        # type or group choices can be wrapped within `(` and `)`, e.g.
        #
        #   attireBlock = (
        #       "bow tie" /
        #       "necktie" /
        #       "Internet attire"
        #   )
        #   attireGroup = (
        #       attire //
        #       attireBlock
        #   )
        propertyType: list[PropertyType] = []
        if len(closingTokens) > 0 and self.peekToken.type == Tokens.SLASH:
            while self.curToken.type not in closingTokens:
                propertyType.extend(self._parsePropertyTypes())
                if self.curToken.type == Tokens.RPAREN:
                    self._nextToken()
                    break

                self._nextToken()

                if self.curToken.type == Tokens.SLASH:
                    self._nextToken()

            if groupName is not None:
                variable = Variable(
                    groupName,
                    isChoiceAddition,
                    propertyType,
                    comments = []
                )

                if self._isOperator():
                    variable.operator = self._parseOperator()

                return variable

            return propertyType

        # parse operator assignments, e.g. `ip4 = (float .ge 0.0) .default 1.0`
        if len(closingTokens) == 1 and self.peekToken.type == Tokens.DOT:
            optype = self._parsePropertyType()
            assert isinstance(optype, str) or isinstance(optype, PropertyReference)
            nativeType = NativeTypeWithOperator(
                optype,
                self._parseOperator()
            )

            self._nextToken() # eat closing token
            if groupName is not None:
                variable = Variable(
                    groupName,
                    isChoiceAddition,
                    nativeType,
                    comments = [],
                    operator = self._parseOperator()
                )

                return variable

            return [nativeType]

        while self.curToken.type not in closingTokens:
            propertyType = []
            comments: list[Comment] = []
            isUnwrapped: bool = False
            hasCut: bool = False
            propertyName = ''

            leadingComment = self._parseComment(True)
            if leadingComment is not None:
                comments.append(leadingComment)

            occurrence = self._parseOccurrences()

            # check if variable name is unwrapped
            if self.curToken.literal == Tokens.TILDE:
                isUnwrapped = True
                self._nextToken() # eat ~

            # parse assignment within array, e.g.
            # ```
            # ActionsPerformActionsParameters = [1* {
            #   typ: "key",
            #   id: text,
            #   actions: ActionItems,
            #   *text => any
            # }]
            # ```
            # or
            # ```
            # script.MappingRemoteValue = [*[(script.RemoteValue / text), script.RemoteValue]];
            # ```
            if (
                self.curToken.literal == Tokens.LBRACE or
                self.curToken.literal == Tokens.LBRACK or
                self.curToken.literal == Tokens.LPAREN
            ):
                innerGroup = self._parseAssignmentValue()
                assert isinstance(innerGroup, PropertyType) or isinstance(innerGroup, list)
                valuesOrProperties.append(Property(
                    hasCut=False,
                    occurrence=occurrence,
                    name='',
                    type=innerGroup,
                    comments=[]
                ))
                continue

            # check if we are in an array and a new item is indicated
            if self.curToken.literal == Tokens.COMMA and closingTokens[0] == Tokens.RBRACK:
                self._nextToken()
                continue

            propertyName = self._parsePropertyName()

            # if `,` is found we have a group reference and jump to the next line
            if self.curToken.type == Tokens.COMMA or self.curToken.type in closingTokens:
                tokenType = self.curToken.type
                parsedComments = False
                comment: Comment | None = None

                # check if line has a comment
                if self.curToken.type == Tokens.COMMA and self.peekToken.type == Tokens.COMMENT:
                    self._nextToken()
                    comment = self._parseComment()
                    parsedComments = True

                propType: str | list[PropertyType]
                if propertyName in PREDEFINED_IDENTIFIER:
                    propType = propertyName
                else:
                    propType = [
                        PropertyReference(
                            'group',
                            propertyName,
                            unwrapped=isUnwrapped
                        )
                    ]
                valuesOrProperties.append(Property(
                    hasCut=hasCut,
                    occurrence=occurrence,
                    name='',
                    type=propType,
                    comments=[comment] if comment is not None else []
                ))

                if self.curToken.literal == Tokens.COMMA or self.curToken.literal == closingTokens[0]:
                    if self.curToken.literal == Tokens.COMMA:
                        self._nextToken()
                    continue

                if not parsedComments:
                    self._nextToken()

                # only continue if next token contains a comma
                if tokenType == Tokens.COMMA:
                    continue

                # otherwise break
                break

            # check if property has cut, which happens if a property is described as
            # - `? "optional-key" ^ => int,`
            # - `? optional-key: int,` - since the colon shortcut includes cuts
            if self.curToken.type == Tokens.CARET or self.curToken.type == Tokens.COLON:
                hasCut = True

                if self.curToken.type == Tokens.CARET:
                    self._nextToken() # eat ^

            # check if we have a group choice instead of an assignment
            if self.curToken.type == Tokens.SLASH and self.peekToken.type == Tokens.SLASH:
                prop = Property(
                    hasCut=hasCut,
                    occurrence=occurrence,
                    name='',
                    type=PropertyReference(
                        type='group',
                        value=propertyName,
                        unwrapped=isUnwrapped
                    ),
                    comments=comments
                )

                if isChoice:
                    # if we already in a choice just push into it
                    assert isinstance(valuesOrProperties[-1], list)
                    valuesOrProperties[-1].append(prop)
                else:
                    # otherwise create a new one
                    isChoice = True
                    valuesOrProperties.append([prop])

                self._nextToken() # eat /
                self._nextToken() # eat /
                continue

            # else if no colon was found, throw
            if not self._isPropertyValueSeparator():
                raise self._parserError('Expected ":" or "=>"')

            self._nextToken() # eat :

            # parse property value
            props = self._parseAssignmentValue()
            operator = self._parseOperator() if self._isOperator() else None
            if isinstance(props, list):
                # property has multiple types (e.g. `float / tstr / int`)
                propertyType.extend(props)
            else:
                propertyType.append(props)

            # advance comma
            flipIsChoice = False
            if self.curToken.type == Tokens.COMMA:
                # if we are in a choice, we leave it here
                flipIsChoice = True

                self._nextToken() # eat ,

            trailingComment = self._parseComment()
            if trailingComment is not None:
                comments.append(trailingComment)

            prop = Property(
                hasCut,
                occurrence,
                propertyName,
                propertyType,
                comments
            )
            if operator is not None:
                prop.operator = operator

            if isChoice:
                assert isinstance(valuesOrProperties[-1], list)
                valuesOrProperties[-1].append(prop)
            else:
                valuesOrProperties.append(prop)

            if flipIsChoice:
                isChoice = False

            # if `}` is found we are at the end of the group
            if self.curToken.type in closingTokens:
                break

            # eat // if we are in a choice
            if isChoice:
                self._nextToken() # eat /
                self._nextToken() # eat /
                continue

        # close segment
        if self.curToken.type == closingTokens[0]:
            self._nextToken()

        # if last closing token is "]" we have an array
        if closingTokens[-1] == Tokens.RBRACK:
            return Array(
                groupName if groupName is not None else '',
                valuesOrProperties,
                comments=[]
            )

        # simplify wrapped types, e.g. from
        # {
        #     "Type": "group",
        #     "Name": "",
        #     "Properties": [
        #         {
        #             "HasCut": false,
        #             "Occurrence": {
        #                 "n": 1,
        #                 "m": 1
        #             },
        #             "Name": "",
        #             "Type": "bool",
        #             "Comment": ""
        #         }
        #     ],
        #     "IsChoiceAddition": false
        # }
        # back to:
        # bool
        if groupName is None and len(valuesOrProperties) == 1 and isinstance(valuesOrProperties[0], Property):
            if valuesOrProperties[0].type in PREDEFINED_IDENTIFIER:
                assert isinstance(valuesOrProperties[0].type, str)
                return [valuesOrProperties[0].type]

        # otherwise a group
        return Group(
            groupName if groupName is not None else '',
            isChoiceAddition,
            valuesOrProperties,
            comments=[]
        )

    def _isPropertyValueSeparator(self) -> bool:
        if self.curToken.type == Tokens.COLON:
            return True

        if self.curToken.type == Tokens.ASSIGN and self.peekToken.type == Tokens.GT:
            self._nextToken() # eat <
            return True

        return False

    
    def _openSegment(self) -> list[str]:
        '''
        checks if group segment is opened and forwards to beginning of
        first property declaration
        @returns {String[]}  closing tokens for group (either `}`, `)` or both)
        '''
        if self.curToken.type == Tokens.LBRACE:
            self._nextToken()

            if self.peekToken.type == Tokens.LPAREN:
                self._nextToken()
                return [Tokens.RPAREN, Tokens.RBRACE]
            return [Tokens.RBRACE]
        elif self.curToken.type == Tokens.LPAREN:
            self._nextToken()
            return [Tokens.RPAREN]
        elif self.curToken.type == Tokens.LBRACK:
            self._nextToken()
            return [Tokens.RBRACK]

        return []

    def _parsePropertyName(self) -> PropertyName:
        # property name without quotes
        if self.curToken.type == Tokens.IDENT or self.curToken.type == Tokens.STRING:
            name = self.curToken.literal
            self._nextToken()
            return name

        raise self._parserError(f'Expected property name, received {self.curToken.type}({self.curToken.literal}), {self.peekToken.type}({self.peekToken.literal})')

    def _parsePropertyType(self) -> PropertyType:
        type: PropertyType
        isUnwrapped: bool = False
        isGroupedRange: bool = False

        # check if variable name is unwrapped
        if self.curToken.literal == Tokens.TILDE:
            isUnwrapped = True
            self._nextToken() # eat ~

        match self.curToken.literal:
            case literal if literal in [t.value for t in Type]:
                type = self.curToken.literal
            case _:
                if self.curToken.literal in BOOLEAN_LITERALS:
                    type = PropertyReference(
                        'literal',
                        self.curToken.literal == 'true',
                        isUnwrapped
                    )
                elif self.curToken.type == Tokens.IDENT:
                    type = PropertyReference(
                        'group',
                        self.curToken.literal,
                        isUnwrapped
                    )
                elif self.curToken.type == Tokens.STRING:
                    type = PropertyReference(
                        'literal',
                        self.curToken.literal,
                        isUnwrapped
                    )
                elif self.curToken.type == Tokens.NUMBER or self.curToken.type == Tokens.FLOAT:
                    type = PropertyReference(
                        'literal',
                        parseNumberValue(self.curToken),
                        isUnwrapped
                    )
                elif self.curToken.type == Tokens.HASH:
                    self._nextToken()
                    n = parseNumberValue(self.curToken)
                    assert isinstance(n, float) or isinstance(n, int)
                    self._nextToken() # eat numeric value
                    self._nextToken() # eat (
                    t = self._parsePropertyType()
                    assert isinstance(t, str)
                    self._nextToken() # eat )
                    type = PropertyReference(
                        'tag',
                        Tag(n, t),
                        isUnwrapped
                    )
                elif self.curToken.literal == Tokens.LPAREN and self.peekToken.type == Tokens.NUMBER:
                    self._nextToken()
                    type = PropertyReference(
                        'literal',
                        parseNumberValue(self.curToken),
                        isUnwrapped
                    )
                    isGroupedRange = True
                else:
                    raise self._parserError(f'Invalid property type "{self.curToken.literal}"')

        # check if type continue as a range
        if (
            self.peekToken.type == Tokens.DOT and
            self._nextToken() and
            self.peekToken.type == Tokens.DOT
        ):
            self._nextToken()
            inclusive = True

            # check if range excludes upper bound
            if self.peekToken.type == Tokens.DOT:
                inclusive = False
                self._nextToken()

            self._nextToken()
            assert isinstance(type, PropertyReference)
            min = type.value
            maxRef = self._parsePropertyType()
            assert isinstance(maxRef, PropertyReference)
            max = maxRef.value
            assert isinstance(min, str) or isinstance(min, float) or isinstance(min, int)
            assert isinstance(max, str) or isinstance(max, float) or isinstance(max, int)
            type = PropertyReference(
                'range',
                Range(min, max, inclusive),
                isUnwrapped
            )

            if isGroupedRange:
                self._nextToken() # eat ")"

        return type

    def _parseOperator(self) -> Operator:
        type = self.peekToken.literal
        if self.curToken.literal != Tokens.DOT or type not in OPERATORS:
            expectedValues = OPERATORS_EXPECTING_VALUES[type]
            if expectedValues is None:
                raise Exception(f'Operator ".{type}" is unknown')
            else:
                raise Exception(f'Operator ".{type}", expects a {" or ".join(expectedValues)} property, but found {self.peekToken.literal}!')
        type = cast(OperatorType, type)

        self._nextToken() # eat "."
        self._nextToken() # eat operator type
        value = self._parsePropertyType()
        self._nextToken() # eat operator value
        return Operator(type, value)

    def _isOperator(self) -> bool:
        return self.curToken.literal == Tokens.DOT and self.peekToken.literal in OPERATORS

    def _parsePropertyTypes(self) -> list[PropertyType]:
        propertyTypes: list[PropertyType] = []

        prop: PropertyType = self._parsePropertyType()
        if self._isOperator():
            assert (isinstance(prop, str) and prop in [t.value for t in Type]) or isinstance(prop, PropertyReference)
            prop = NativeTypeWithOperator(
                prop,
                self._parseOperator()
            )
        else:
            self._nextToken() # eat `/`

        propertyTypes.append(prop)

        # ensure we don't go into the next choice, e.g.:
        # ```
        # delivery = (
        #   city // lala: tstr / bool // per-pickup: true,
        # )
        if self.curToken.type == Tokens.SLASH and self.peekToken.type == Tokens.SLASH:
            return propertyTypes

        # capture more if available (e.g. `tstr / float / boolean`)
        while self.curToken.type == Tokens.SLASH:
            self._nextToken() # eat `/`
            propertyTypes.append(self._parsePropertyType())
            self._nextToken()

            # ensure we don't go into the next choice, e.g.:
            # ```
            # delivery = (
            #   city // lala: tstr / bool // per-pickup: true,
            # )
            if self.curToken.type == Tokens.SLASH and self.peekToken.type == Tokens.SLASH:
                break

        return propertyTypes

    def _parseOccurrences(self) -> Occurrence:
        occurrence = DEFAULT_OCCURRENCE

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
            if self.peekToken.type == Tokens.NUMBER:
                m = int(self.peekToken.literal)
                self._nextToken()

            occurrence = Occurrence(n, m)
            self._nextToken()
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
            self._nextToken() # eat "n"
            self._nextToken() # eat "*"

            # check if there is a max definition
            if self.curToken.type == Tokens.NUMBER:
                m = int(self.curToken.literal)
                self._nextToken()

            occurrence = Occurrence(n, m)

        return occurrence

    def _parseComment(self, isLeading: bool = False) -> Comment | None:
        if self.curToken.type != Tokens.COMMENT:
            return None
        comment = re.sub(r'^;(\s*)', '', self.curToken.literal)
        self._nextToken()

        if len(comment.strip()) == 0:
            return None

        return Comment(comment, isLeading)

    def parse(self) -> list[Assignment]:
        definition: list[Assignment] = []

        while (self.curToken.type != Tokens.EOF):
            group = self._parseAssignments()
            if group is not None:
                definition.append(group)

        return definition

    def _parserError(self, message: str) -> Exception:
        location = self.l.getLocation()
        locInfo = self.l.getLocationInfo()
        return Exception(f'{location.line + 1}:{location.position} - error: {message}\n\n{locInfo}')
