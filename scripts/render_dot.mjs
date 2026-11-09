import { readFileSync, writeFileSync } from "node:fs";
import { instance } from "@viz-js/viz";

const [, , dotPath, outPath] = process.argv;
if (!dotPath || !outPath) {
  console.error("usage: node render_dot.mjs <input.dot> <output.svg>");
  process.exit(2);
}

const dot = readFileSync(dotPath, "utf8");
const viz = await instance();
writeFileSync(outPath, viz.renderString(dot, { format: "svg" }));
