<template>
  <div class="nutrition-chart">
    <v-chart :option="chartOption" autoresize style="height:260px" />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { PieChart } from "echarts/charts";
import { TitleComponent, TooltipComponent, LegendComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

use([PieChart, TitleComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

interface NutritionData {
  calories?: number;
  protein?: number;
  fat?: number;
  carbohydrates?: number;
  fiber?: number;
  sugar?: number;
  sodium?: number;
}

const props = defineProps<{ nutrition: NutritionData }>();

const chartOption = computed(() => {
  const n = props.nutrition;
  const items = [
    { name: "蛋白质", value: n.protein || 0 },
    { name: "脂肪", value: n.fat || 0 },
    { name: "碳水", value: n.carbohydrates || 0 },
    { name: "纤维", value: n.fiber || 0 },
    { name: "糖", value: n.sugar || 0 },
    { name: "钠", value: (n.sodium || 0) / 1000 }, // convert mg to g for display
  ].filter((x) => x.value > 0);

  return {
    title: { text: `热量: ${n.calories?.toFixed(0) || 0} kcal`, left: "center",
              textStyle: { fontSize: 14 } },
    tooltip: { trigger: "item", formatter: "{b}: {c}g ({d}%)" },
    legend: { bottom: 0 },
    series: [{
      type: "pie", radius: ["45%", "75%"], center: ["50%", "50%"],
      data: items, label: { formatter: "{b}\n{d}%" },
    }],
  };
});
</script>
