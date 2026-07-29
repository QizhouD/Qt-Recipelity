// ── jsdom polyfills ─────────────────────────────────────────────────────

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

// ── Mock vue-echarts to avoid Canvas/zrender errors in jsdom ──────────

// We mock the entire vue-echarts module so that ECharts never attempts
// to create a real Canvas context. All tests that need chart logic should
// test the computed chartOption, not the rendered output.
