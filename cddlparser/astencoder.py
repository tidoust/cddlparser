from __future__ import annotations
from typing import Any, Union
from json import JSONEncoder
from math import inf
from .ast import CDDLNode
from .tokens import Token


class ASTEncoder(JSONEncoder):
    """
    JSON encoder for an abstract syntax tree (AST)

    The AST is mostly serializable already except that:
    1. tree nodes link back to their parent node which creates cycles;
    2. an unconstrained occurrence value is represented with Infinity, which
    does not exist in JSON.

    The encoder simply skips `parentNode` keys and Infinity values.

    The encoder also skips None values to make the results slightly more
    compact.

    Use with code such as `json.dumps(ast, indent=2, cls=ASTEncoder)`.
    """

    def default(self, o: Union[CDDLNode, Token]) -> dict[str, Any]:
        dic = {
            key: value
            for key, value in o.__dict__.items()
            if key != "parentNode" and value is not None and value != inf
        }
        return dic
