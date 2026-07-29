// Mock vue-echarts for jsdom test environments (no Canvas API)
import { defineComponent, h } from "vue";

const MockVChart = defineComponent({
  name: "VChart",
  props: { option: Object, autoresize: Boolean },
  setup(props) {
    // Render a plain div with a data attribute so tests can inspect the option
    return () =>
      h("div", {
        class: "v-chart-mock",
        "data-testid": "echarts-mock",
        "data-option": JSON.stringify(props.option),
      });
  },
});

export default MockVChart;
export { MockVChart as VChart };
