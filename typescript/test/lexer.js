import { describe, it } from "node:test";
import assert from "node:assert";
import { Tokens, Token } from "../dist/tokens.js";
import { Lexer } from "../dist/lexer.js";

describe("TestLexer", () => {
  it("should allow to read token", () => {
    const cddl = "=+(){},/";
    const tests = [
      Tokens.ASSIGN,
      Tokens.PLUS,
      Tokens.LPAREN,
      Tokens.RPAREN,
      Tokens.LBRACE,
      Tokens.RBRACE,
      Tokens.COMMA,
      Tokens.TCHOICE,
    ];

    const lexer = new Lexer(cddl);
    for (const tokenType of tests) {
      const token = lexer.nextToken();
      assert.strictEqual(token.type, tokenType);
    }
  });

  it("should read identifiers and comments", () => {
    const cddl = "   headers,       \n   ; Headers for the recipient";
    const comment = new Token(
      Tokens.COMMENT,
      "; Headers for the recipient",
      [],
      "       \n   "
    );
    const tests = [
      [Tokens.IDENT, "headers", "   ", null],
      [Tokens.COMMA, "", "", null],
      [Tokens.EOF, "", "", comment],
    ];

    const lexer = new Lexer(cddl);
    for (const [tokenType, literal, whitespace, expectedComment] of tests) {
      const token = lexer.nextToken();
      assert.strictEqual(token.type, tokenType);
      assert.strictEqual(token.literal, literal);
      assert.strictEqual(token.whitespace, whitespace);
      if (expectedComment === null) {
        assert.strictEqual(token.comments.length, 0);
      } else {
        assert.strictEqual(token.comments.length, 1);
        assert.strictEqual(token.comments[0].type, expectedComment.type);
        assert.strictEqual(token.comments[0].literal, expectedComment.literal);
        assert.strictEqual(token.comments[0].whitespace, expectedComment.whitespace);
      }
    }
  });
});
