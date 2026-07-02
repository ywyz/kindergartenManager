import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      "@kindergarten/contracts": resolve(root, "packages/contracts/src/index.ts")
    }
  },
  test: {
    include: ["evals/**/*.eval.test.ts"],
    passWithNoTests: false
  }
});
