from .parser import Parser
from .ast import Marker
from .tokens import Token, Tokens
from . import ast

__all__ = ["Marker", "Token", "Tokens", "ast"]


def parse(string) -> ast.CDDLTree:
    parser = Parser(string)
    return parser.parse()
