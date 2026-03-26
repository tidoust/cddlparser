from .parser import Parser
from .ast import Marker
from .astencoder import ASTEncoder
from .errors import ParserError
from .tokens import Token, Tokens
from . import ast

__all__ = ["Marker", "Token", "Tokens", "ParserError", "ast", "ASTEncoder"]


def parse(string: str) -> ast.CDDLTree:
    parser = Parser(string)
    return parser.parse()
