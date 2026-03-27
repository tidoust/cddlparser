import path from "path";
import * as fs from "fs";
import { fileURLToPath } from "url";
import { Parser } from "./parser.ts";
import { CDDLTree } from "./ast.ts";

/**
 * Parse a CDDL string and return the resulting abstract syntax tree.
 *
 * @param string The CDDL string to parse
 * @returns The abstract syntax tree
 */
export function parse(string: string): CDDLTree {
  const parser = new Parser(string);
  return parser.parse();
}

/**
 * Main entry point for the script when run from the command-line.
 */
function main(): void {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.log("Please provide a CDDL file as parameter");
    console.log("Ex: node typescript/cddlparser.js tests/__fixtures__/example.cddl");
  } else {
    const file = args[0]!;
    try {
      const cddl = fs.readFileSync(path.join('.', file), { encoding: "utf8" });
      const ast = parse(cddl);

      console.log("Abstract syntax tree (AST)");
      console.log("--------------------");
      console.log(ast.toString());

      console.log();
      console.log("JSON serialization");
      console.log(JSON.stringify(ast, null, 2));

      console.log();
      console.log("AST re-serialization");
      console.log("--------------------");
      console.log(ast.serialize());
    } catch (err) {
      console.error(`Error reading or parsing file: ${(err as Error).message}`);
    }
  }
}

// Run the main function if the script is executed directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}
