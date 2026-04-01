<template>
  <div class="year-display">
    <div class="year-title">Current Year</div>
    <div class="year-value">{{ currentYear }}</div>
    <YearSlider />
  </div>
  <PiePlot />
  <LineChart />
</template>

<script setup>
import YearSlider from '@/components/YearSlider.vue';
import { useYearStore } from '@/stores/yearStore'
import { storeToRefs } from 'pinia'

import PiePlot from './piePlot/index.vue'
import LineChart from './LocallineChart/index.vue'

const yearStore = useYearStore()
const { currentYear } = storeToRefs(yearStore)

</script>

<style scoped>
.year-display {
  text-align: center;
  font-size: 1.2em;
  font-weight: bold;
  background-color: var(--vp-c-bg-soft);
}

.year-title {
  font-size: 0.6em;
  color: var(--vp-c-text-2);
}

.year-value {
  font-size: 1.5em;
  color: #006d5b;
  font-weight: bold;
}
</style>