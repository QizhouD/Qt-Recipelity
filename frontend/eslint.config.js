import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import tsParser from "@typescript-eslint/parser";

export default [
  // ── Global ignores ───────────────────────────────────────────────────
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "playwright-report/**",
      "test-results/**",
      "*.config.*",
      "vitest.setup.ts",
    ],
  },

  // ── Base JS recommended rules ────────────────────────────────────────
  js.configs.recommended,

  // ── Vue essential rules ──────────────────────────────────────────────
  ...pluginVue.configs["flat/essential"],

  // ── .ts files (standalone TypeScript) ────────────────────────────────
  {
    files: ["**/*.ts"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
      },
    },
  },

  // ── .vue files (Vue SFC) — vue-eslint-parser + TypeScript ───────────
  {
    files: ["**/*.vue"],
    languageOptions: {
      parserOptions: {
        parser: tsParser,
        ecmaVersion: "latest",
        sourceType: "module",
      },
    },
  },

  // ── Browser globals ──────────────────────────────────────────────────
  {
    files: ["src/**/*.{ts,vue}"],
    languageOptions: {
      globals: {
        console: "readonly",
        document: "readonly",
        window: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        FormData: "readonly",
        File: "readonly",
        Blob: "readonly",
        URL: "readonly",
        fetch: "readonly",
        Response: "readonly",
        Request: "readonly",
        HTMLElement: "readonly",
        HTMLCanvasElement: "readonly",
        sessionStorage: "readonly",
        localStorage: "readonly",
        AbortController: "readonly",
        DOMException: "readonly",
        BeforeUnloadEvent: "readonly",
        ResizeObserver: "readonly",
        NodeJS: "readonly",
      },
    },
    rules: {
      "no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "no-console": "off",
    },
  },

  // ── Test files ───────────────────────────────────────────────────────
  {
    files: ["src/**/*.{test,spec}.ts", "e2e/**/*.ts"],
    languageOptions: {
      parser: tsParser,
      globals: {
        describe: "readonly",
        it: "readonly",
        test: "readonly",
        expect: "readonly",
        beforeEach: "readonly",
        afterEach: "readonly",
        beforeAll: "readonly",
        afterAll: "readonly",
        vi: "readonly",
        globalThis: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "off",
    },
  },

  // ── Single-word component exceptions ─────────────────────────────────
  {
    files: ["src/views/About.vue", "src/views/NotFound.vue"],
    rules: {
      "vue/multi-word-component-names": "off",
    },
  },
];
