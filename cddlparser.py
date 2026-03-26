import json
import sys
from cddlparser.parser import Parser
from cddlparser.ast import CDDLTree
from cddlparser.astencoder import ASTEncoder

def parse(string) -> CDDLTree:
    parser = Parser(string)
    return parser.parse()


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Please provide a CDDL file as parameter")
        print("Ex: python cddlparser.py tests/__fixtures__/example.cddl")
    else:
        file = sys.argv[1]
        with open(file, "r", encoding="utf8") as fhandle:
            cddl = fhandle.read()
            ast = parse(cddl)
            print("Abstract syntax tree (AST)")
            print("--------------------")
            print(ast)

            print()
            print("JSON serialization")
            print(json.dumps(ast, indent=2, cls=ASTEncoder))

            print()
            print("AST re-serialization")
            print("--------------------")
            print(ast.serialize())
