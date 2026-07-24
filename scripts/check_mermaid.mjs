#!/usr/bin/env node
// Parse every ```mermaid block in the repo's markdown and fail on syntax errors.
// Diagrams are only ever rendered by a viewer, so a broken one is invisible until someone opens
// the file — ARCHITECTURE.md shipped two parse errors this way (a reserved `graph` subgraph id and
// a `;` inside a sequence message, which Mermaid reads as a statement separator).
//
// Usage: node scripts/check_mermaid.mjs [file.md ...]      (default: all tracked markdown)
// Needs mermaid on the module path: npm i --no-save mermaid jsdom

import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { JSDOM } from "jsdom";

// `git ls-files` over a glob crawl: it already knows what is tracked, so .venv/, node_modules/ and
// every other ignored path are excluded for free, and dot-directories are not special-cased.
const tracked = () =>
  execFileSync("git", ["ls-files", "-z", "*.md"], { encoding: "utf8" }).split("\0").filter(Boolean);

const args = process.argv.slice(2);
const files = args.length ? args : tracked();

// mermaid.parse() still sanitizes label text through DOMPurify, which needs a real DOM. Without
// this shim every non-trivial diagram fails with "DOMPurify.addHook is not a function" — a false
// positive indistinguishable from a genuine syntax error.
const { window } = new JSDOM("<!doctype html><body></body>", { pretendToBeVisual: true });
globalThis.window = window;
for (const key of ["document", "navigator", "Element", "SVGElement", "Node", "MutationObserver"]) {
  globalThis[key] ??= window[key];
}

const mermaid = (await import("mermaid")).default;
mermaid.initialize({ startOnLoad: false });

let checked = 0;
let failed = 0;

for (const file of files) {
  const source = await readFile(file, "utf8");
  for (const match of source.matchAll(/```mermaid\r?\n([\s\S]*?)```/g)) {
    const line = source.slice(0, match.index).split("\n").length;
    const kind = match[1].trim().split("\n")[0];
    checked += 1;
    try {
      await mermaid.parse(match[1]);
    } catch (error) {
      failed += 1;
      console.error(`\n${file}:${line}  invalid mermaid (${kind})`);
      console.error(String(error?.message ?? error).replace(/^/gm, "    "));
    }
  }
}

console.log(`\nchecked ${checked} mermaid block(s) in ${files.length} file(s): ${failed} invalid`);
process.exit(failed ? 1 : 0);
