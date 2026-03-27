import { describe, it } from "node:test";
import assert from "node:assert";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { Parser } from "../dist/parser.js";

const scriptPath = path.dirname(fileURLToPath(import.meta.url));
const fixturesPath = path.join(scriptPath, "..", "..", "tests", "__fixtures__");
const snapshotsPath = path.join(scriptPath, "..", "..", "tests", "__snapshots__");

describe("TestParser", () => {
  const files = fs.readdirSync(fixturesPath).filter((f) => {
    return fs.statSync(path.join(fixturesPath, f)).isFile();
  });

  const rfcPath = path.join(fixturesPath, "rfc");
  const rfcs = fs.existsSync(rfcPath)
    ? fs.readdirSync(rfcPath).filter((f) => {
        return fs.statSync(path.join(rfcPath, f)).isFile();
      })
    : [];

  describe("parse CDDL", () => {
    for (const file of files) {
      it(`should parse ${file}`, () => {
        testParseFile(file);
      });
    }
  });

  describe("serialize CDDL", () => {
    for (const file of files) {
      it(`should serialize ${file}`, () => {
        testSerializeFile("", file);
      });
    }
  });

  describe("serialize RFC", () => {
    for (const file of rfcs) {
      it(`should serialize RFC ${file}`, () => {
        testSerializeFile("rfc", file);
      });
    }
  });
});

function testParseFile(file) {
  const cddlPath = path.join(fixturesPath, file);
  const cddl = fs.readFileSync(cddlPath, "utf8").replace(/\r\n/g, '\n');
  const parser = new Parser(cddl);
  const ast = parser.parse();

  const snapName = file.replace(/\.cddl$/, ".snap");
  const snapfile = path.join(snapshotsPath, snapName);

  if (fs.existsSync(snapfile)) {
    // Compare with snapshot if it exists
    const snap = fs.readFileSync(snapfile, "utf8").replace(/\r\n/g, '\n');
    assert.strictEqual(ast.toString(), snap);
  } else {
    // Create the snapshot if it does not exist yet
    // Note: ensure snapshotsPath exists
    if (!fs.existsSync(snapshotsPath)) {
      fs.mkdirSync(snapshotsPath, { recursive: true });
    }
    fs.writeFileSync(snapfile, ast.toString(), "utf8");
  }
}

function testSerializeFile(subpath, file) {
  const cddlPath = path.join(fixturesPath, subpath, file);
  const cddl = fs.readFileSync(cddlPath, "utf8").replace(/\r\n/g, '\n');
  const parser = new Parser(cddl);
  const ast = parser.parse();
  const serialization = ast.serialize();
  assert.strictEqual(serialization, cddl);
}
