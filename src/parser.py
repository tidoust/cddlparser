from pprint import pprint
import json
import re
from typing import Optional, cast

from .lexer import Lexer
from .tokens import Token, Tokens
from .constants import PREDEFINED_IDENTIFIER, BOOLEAN_LITERALS
from .utils import parseNumberValue
from .ast import CDDLTree, AstNode, Property, Type, PropertyType, PropertyTypes, StrPropertyType, PropertyReference, Variable, RangePropertyReference, Occurrence, Assignment, Comment, Group, Array, OperatorType, NativeTypeWithOperator, Operator, Tag, Range


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

    def _nextToken(self) -> Token:
        curToken = self.curToken
        self.curToken = self.peekToken
        self.peekToken = self.l.nextToken()
        return curToken

    def _parseAssignment(self) -> Assignment:
        children: list[AstNode] = []
        comments: list[Comment] = []
        while (self.curToken.type == Tokens.COMMENT):
            comment = self._parseComment()
            assert comment is not None
            comments.append(comment)
            children.append(comment)

        # expect group identifier, e.g.
        # groupName =
        # groupName /=
        # groupName //=
        if (self.curToken.type != Tokens.IDENT or
                not (self.peekToken.type == Tokens.ASSIGN or
                    self.peekToken.type == Tokens.SLASH)):
            raise self._parserError(f'group identifier expected, received "{self.curToken.str()}"')

        isChoiceAddition = False
        groupName = self.curToken.literal
        children.append(self._nextToken()) # eat group identifier

        if self.curToken.type == Tokens.SLASH:
            isChoiceAddition = True
            children.append(self._nextToken()) # eat `/`

        if self.curToken.type == Tokens.SLASH:
            children.append(self._nextToken()) # eat `/`

        children.append(self._nextToken()) # eat `=`
        assignmentValue = self._parseAssignmentValue(groupName, isChoiceAddition)
        assert isinstance(assignmentValue, Assignment)
        children.extend(assignmentValue.children)

        while (self.curToken.type == Tokens.COMMENT):
            comment = self._parseComment()
            if comment is not None:
                comments.append(comment)
                children.append(comment)
        assignmentValue.comments = comments

        assignmentValue.children = children
        return assignmentValue

    def _parseAssignmentValue(self, groupName: Optional[str] = None, isChoiceAddition: bool = False) -> Assignment | PropertyTypes:
        node: AstNode
        children: list[AstNode] = []
        closingTokens = self._openSegment(children)

        # if no group segment was opened we have a variable assignment
        # and can return immediatelly, e.g.
        #
        #   attire = "bow tie" / "necktie" / "Internet attire"
        #
        if len(closingTokens) == 0:
            types = self._parsePropertyTypes()
            if groupName is not None:
                variable = Variable(
                    groupName,
                    isChoiceAddition,
                    types,
                    comments = []
                )
                variable.children.append(types)
                return variable
            return types

        
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
        propertyTypes: list[PropertyType] = []
        if len(closingTokens) > 0 and self.peekToken.type == Tokens.SLASH:
            while self.curToken.type not in closingTokens:
                types = self._parsePropertyTypes()
                children.extend(types.children)
                propertyTypes.extend(types.types)
                if self.curToken.type == Tokens.RPAREN:
                    break

                if self.curToken.type == Tokens.SLASH:
                    children.append(self._nextToken())
                if self.curToken.type == Tokens.SLASH:
                    children.append(self._nextToken())
            children.append(self._nextToken())

            node = PropertyTypes(propertyTypes)
            node.children = children

            if groupName is not None:
                variable = Variable(
                    groupName,
                    isChoiceAddition,
                    node,
                    comments = []
                )
                variable.children.append(node)

                if self._isOperator():
                    variable.operator = self._parseOperator()
                    variable.children.append(variable.operator)

                return variable

            return node

        # parse operator assignments, e.g. `ip4 = (float .ge 0.0) .default 1.0`
        if len(closingTokens) == 1 and self.peekToken.type == Tokens.DOT:
            optype = self._parsePropertyType()
            assert isinstance(optype, StrPropertyType) or isinstance(optype, PropertyReference)
            nativeType = NativeTypeWithOperator(optype, self._parseOperator())
            children.append(nativeType)
            assert groupName is None

            node = PropertyTypes([nativeType])
            children.append(self._nextToken()) # eat closing token
            node.children = children
            return node

        hasCut = False
        isChoice = False
        valuesOrProperties: list[Property | list[Property]] = []
        while self.curToken.type not in closingTokens:
            comments: list[Comment] = []
            leadingComment = self._parseComment(True)
            if leadingComment is not None:
                comments.append(leadingComment)
                children.append(leadingComment)

            occurrence = self._parseOccurrence()
            children.append(occurrence)

            # check if variable name is unwrapped
            isUnwrapped: bool = False
            if self.curToken.type == Tokens.TILDE:
                isUnwrapped = True
                children.append(self._nextToken()) # eat ~

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
                self.curToken.type == Tokens.LBRACE or
                self.curToken.type == Tokens.LBRACK or
                self.curToken.type == Tokens.LPAREN
            ):
                innerGroup = self._parseAssignmentValue()
                innerProp = Property(
                    hasCut=False,
                    occurrence=occurrence,
                    name='',
                    type=innerGroup,
                    comments=[]
                )
                innerProp.children.append(innerGroup)
                valuesOrProperties.append(innerProp)
                children.append(innerProp)
                continue

            # check if we are in an array and a new item is indicated
            if self.curToken.type == Tokens.COMMA and closingTokens[0] == Tokens.RBRACK:
                children.append(self._nextToken())
                continue

            propertyName = self._parsePropertyName()
            children.append(propertyName)

            # if `,` is found we have a group reference and jump to the next line
            if self.curToken.type == Tokens.COMMA or self.curToken.type in closingTokens:
                tokenType = self.curToken.type
                parsedComments = False
                comment: Comment | None = None

                # check if line has a comment
                if self.curToken.type == Tokens.COMMA and self.peekToken.type == Tokens.COMMENT:
                    children.append(self._nextToken())
                    comment = self._parseComment()
                    assert comment is not None
                    children.append(comment)
                    parsedComments = True

                propType: StrPropertyType | list[PropertyType]
                wrappedPropType: PropertyType | PropertyTypes
                if propertyName.literal in PREDEFINED_IDENTIFIER:
                    propType = StrPropertyType(propertyName.literal)
                    wrappedPropType = propType
                else:
                    wrappedPropType = PropertyTypes([
                        PropertyReference(
                            'group',
                            propertyName.literal,
                            unwrapped=isUnwrapped
                        )
                    ])
                propProp = Property(
                    hasCut=hasCut,
                    occurrence=occurrence,
                    name='',
                    type=wrappedPropType,
                    comments=[comment] if comment is not None else []
                )
                valuesOrProperties.append(propProp)

                if self.curToken.type == Tokens.COMMA or self.curToken.type == closingTokens[0]:
                    if self.curToken.type == Tokens.COMMA:
                        children.append(self._nextToken())
                    continue

                if not parsedComments:
                    children.append(self._nextToken())

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
                    children.append(self._nextToken()) # eat ^

            # check if we have a group choice instead of an assignment
            if self.curToken.type == Tokens.SLASH and self.peekToken.type == Tokens.SLASH:
                prop = Property(
                    hasCut=hasCut,
                    occurrence=occurrence,
                    name='',
                    type=PropertyReference(
                        type='group',
                        value=propertyName.literal,
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

                children.append(self._nextToken()) # eat /
                children.append(self._nextToken()) # eat /
                continue

            # else if no colon was found, throw
            if not self._isPropertyValueSeparator():
                raise self._parserError('Expected ":" or "=>"')
            if self.curToken.type == Tokens.ASSIGN:
                children.append(self._nextToken()) # eat =
            children.append(self._nextToken()) # eat : or >

            # parse property value
            propTypes: list[PropertyType] = []
            props = self._parseAssignmentValue()
            operator = self._parseOperator() if self._isOperator() else None
            if isinstance(props, PropertyTypes):
                # property has multiple types (e.g. `float / tstr / int`)
                propTypes.extend(props.types)
            else:
                propTypes.append(props)
            children.append(props)
            if operator is not None:
                children.append(operator)

            # advance comma
            flipIsChoice = False
            if self.curToken.type == Tokens.COMMA:
                # if we are in a choice, we leave it here
                flipIsChoice = True

                children.append(self._nextToken()) # eat ,

            trailingComment = self._parseComment()
            if trailingComment is not None:
                comments.append(trailingComment)
                children.append(trailingComment)

            prop = Property(
                hasCut,
                occurrence,
                propertyName.literal,
                PropertyTypes(propTypes),
                comments,
                operator
            )

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
                children.append(self._nextToken()) # eat /
                children.append(self._nextToken()) # eat /
                continue

        # close segment
        if self.curToken.type == closingTokens[0]:
            children.append(self._nextToken())

        # if last closing token is "]" we have an array
        if closingTokens[-1] == Tokens.RBRACK:
            node = Array(
                groupName if groupName is not None else '',
                valuesOrProperties,
                comments=[]
            )
            node.children = children
            return node

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
                node = PropertyTypes([StrPropertyType(valuesOrProperties[0].type)])
                node.children = children
                return node

        # otherwise a group
        node = Group(
            groupName if groupName is not None else '',
            isChoiceAddition,
            valuesOrProperties,
            comments=[]
        )
        node.children = children

        if self._isOperator():
            node.operator = self._parseOperator()
            node.children.append(node.operator)
        return node

    def _isPropertyValueSeparator(self) -> bool:
        if self.curToken.type == Tokens.COLON:
            return True

        if self.curToken.type == Tokens.ASSIGN and self.peekToken.type == Tokens.GT:
            return True

        return False

    
    def _openSegment(self, children: list[AstNode]) -> list[str]:
        '''
        checks if group segment is opened and forwards to beginning of
        first property declaration
        @returns {String[]}  closing tokens for group (either `}`, `)` or both)
        '''
        if self.curToken.type == Tokens.LBRACE:
            children.append(self._nextToken())

            if self.peekToken.type == Tokens.LPAREN:
                children.append(self._nextToken())
                return [Tokens.RPAREN, Tokens.RBRACE]
            return [Tokens.RBRACE]
        elif self.curToken.type == Tokens.LPAREN:
            children.append(self._nextToken())
            return [Tokens.RPAREN]
        elif self.curToken.type == Tokens.LBRACK:
            children.append(self._nextToken())
            return [Tokens.RBRACK]

        return []

    def _parsePropertyName(self) -> Token:
        if self.curToken.type == Tokens.IDENT or self.curToken.type == Tokens.STRING:
            name = self.curToken
            self._nextToken()
            return name

        raise self._parserError(f'Expected property name, received {self.curToken.type}({self.curToken.literal}), {self.peekToken.type}({self.peekToken.literal})')

    def _parsePropertyType(self) -> PropertyType:
        children: list[AstNode] = []
        type: PropertyType
        isUnwrapped = False
        isGroupedRange = False
        tokenRead = False

        # check if variable name is unwrapped
        if self.curToken.type == Tokens.TILDE:
            isUnwrapped = True
            children.append(self._nextToken()) # eat ~

        match self.curToken.literal:
            case literal if literal in [t.value for t in Type]:
                type = StrPropertyType(self.curToken.literal)
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
                    children.append(self._nextToken())
                    tagChildren: list[AstNode] = []
                    n = parseNumberValue(self.curToken)
                    assert isinstance(n, float) or isinstance(n, int)
                    tagChildren.append(self._nextToken()) # eat numeric value
                    tagChildren.append(self._nextToken()) # eat (
                    t = self._parsePropertyType()
                    assert isinstance(t, StrPropertyType)
                    tagChildren.append(t)
                    tagChildren.append(self._nextToken()) # eat )
                    tag = Tag(n, t.value)
                    tag.children = tagChildren
                    children.append(tag)
                    type = PropertyReference(
                        'tag',
                        tag,
                        isUnwrapped
                    )
                    tokenRead = True
                elif self.curToken.type == Tokens.LPAREN and self.peekToken.type == Tokens.NUMBER:
                    children.append(self._nextToken())
                    type = PropertyReference(
                        'literal',
                        parseNumberValue(self.curToken),
                        isUnwrapped
                    )
                    isGroupedRange = True
                else:
                    raise self._parserError(f'Invalid property type "{self.curToken.literal}"')
        if not tokenRead:
            children.append(self._nextToken())

        # check if type continue as a range
        if self.curToken.type == Tokens.INCLRANGE or self.curToken.type == Tokens.EXCLRANGE:
            inclusive = (self.curToken.type != Tokens.EXCLRANGE)
            children.append(self._nextToken())

            assert isinstance(type, PropertyReference)
            min = type.value
            maxRef = self._parsePropertyType()
            children.extend(maxRef.children)
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
                children.append(self._nextToken()) # eat ")"

        type.children = children
        return type

    def _parseOperator(self) -> Operator:
        children: list[AstNode] = []
        type = self.peekToken.literal
        if self.curToken.type != Tokens.DOT or type not in OPERATORS:
            expectedValues = OPERATORS_EXPECTING_VALUES[type]
            if expectedValues is None:
                raise Exception(f'Operator ".{type}" is unknown')
            else:
                raise Exception(f'Operator ".{type}", expects a {" or ".join(expectedValues)} property, but found {self.peekToken.literal}!')
        type = cast(OperatorType, type)

        children.append(self._nextToken()) # eat "."
        children.append(self._nextToken()) # eat operator type
        value = self._parsePropertyType()
        children.append(value)
        node = Operator(type, value)
        node.children = children
        return node

    def _isOperator(self) -> bool:
        return self.curToken.type == Tokens.DOT and self.peekToken.literal in OPERATORS

    def _parsePropertyTypes(self) -> PropertyTypes:
        children: list[AstNode] = []
        propertyTypes: list[PropertyType] = []

        prop: PropertyType = self._parsePropertyType()
        if self._isOperator():
            assert (isinstance(prop, StrPropertyType) and prop.value in [t.value for t in Type]) or isinstance(prop, PropertyReference)
            prop = NativeTypeWithOperator(prop, self._parseOperator())
        propertyTypes.append(prop)
        children.append(prop)

        # ensure we don't go into the next choice, e.g.:
        # ```
        # delivery = (
        #   city // lala: tstr / bool // per-pickup: true,
        # )
        if self.curToken.type == Tokens.SLASH and self.peekToken.type == Tokens.SLASH:
            node = PropertyTypes(propertyTypes)
            node.children = children
            return node

        # capture more if available (e.g. `tstr / float / boolean`)
        while self.curToken.type == Tokens.SLASH:
            children.append(self._nextToken()) # eat `/`
            type = self._parsePropertyType()
            propertyTypes.append(type)
            children.append(type)

            # ensure we don't go into the next choice, e.g.:
            # ```
            # delivery = (
            #   city // lala: tstr / bool // per-pickup: true,
            # )
            if self.curToken.type == Tokens.SLASH and self.peekToken.type == Tokens.SLASH:
                break

        node = PropertyTypes(propertyTypes)
        node.children = children
        return node

    def _parseOccurrence(self) -> Occurrence:
        children: list[AstNode] = []
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

        occurrence.children = children
        return occurrence

    def _parseComment(self, isLeading: bool = False) -> Comment | None:
        if self.curToken.type != Tokens.COMMENT:
            return None
        comment = re.sub(r'^;(\s*)', '', self.curToken.literal)
        children: list[AstNode] = []
        children.append(self._nextToken())

        node = Comment(comment, isLeading)
        node.children = children
        return node

    def parse(self) -> CDDLTree:
        definition: list[Assignment] = []

        while (self.curToken.type != Tokens.EOF):
            group = self._parseAssignment()
            definition.append(group)

        # Add EOF token to the end of the tree so that serialization preserve
        # final whitespaces
        definition[-1].children.append(self._nextToken())
        return CDDLTree(definition)

    def _parserError(self, message: str) -> Exception:
        location = self.l.getLocation()
        locInfo = self.l.getLocationInfo()
        return Exception(f'{location.line + 1}:{location.position} - error: {message}\n\n{locInfo}')
