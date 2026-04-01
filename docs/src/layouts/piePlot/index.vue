<template>

      <div class="card-header">
        <h3 class="region-title">{{ regionName }}</h3>
      </div>

    <card>
      <svg ref="chartSvg" class="chart-svg"></svg>
    </card>
    

</template>

<script setup>
import { computed, ref, watchEffect } from 'vue';
import { useYearStore } from '@/stores/yearStore';
import { storeToRefs } from 'pinia';
import { useMapStore } from '@/stores/mapStore';
import { drawPieChart } from './svg';

import Card from './card.vue';

const yearStore = useYearStore();
const { currentYear } = storeToRefs(yearStore);

const mapStore = useMapStore();
const selectedRegion = computed(() => mapStore.selectedRegion ? mapStore.selectedRegion.properties : null);

const regionName = computed(() => {
  return selectedRegion.value?.NAME_1_x +" "+ selectedRegion.value?.NAME_2_x || 'Unknown Region';
});

const totalValue = computed(() => {
  if (!selectedRegion.value) return 0;
  const year = currentYear.value;
  const totalKey = `Year${year}`;
  return Number(selectedRegion.value[totalKey]) || 0;
});

const dcValue = computed(() => {
  if (!selectedRegion.value) return 0;
  const year = currentYear.value;
  const dcKey = `Year${year}_dc`;
  return Number(selectedRegion.value[dcKey]) || 0;
});

const l1Value = computed(() => {
  if (!selectedRegion.value) return 0;
  const year = currentYear.value;
  const l1Key = `Year${year}_l1`;
  return Number(selectedRegion.value[l1Key]) || 0;
});

const l2Value = computed(() => {
  if (!selectedRegion.value) return 0;
  const year = currentYear.value;
  const l2Key = `Year${year}_l2`;
  return Number(selectedRegion.value[l2Key]) || 0;
});


const pieData = computed(() => {
  if (!selectedRegion.value) {
    return [{ type: 'empty', value: 1 }];
  }
  
  const total = totalValue.value;
  const dc = dcValue.value;
  const l1 = l1Value.value;
  const l2 = l2Value.value;

  if (total === 0 || (dc === 0 && l1 === 0 && l2 === 0)) {
    return [{ type: 'empty', value: 1 }];
  }

  const totalNonZero = total > 0 ? total : 1;
  const data = [
    { type: 'dc', value: dc / totalNonZero },
    { type: 'l1', value: l1 / totalNonZero },
    { type: 'l2', value: l2 / totalNonZero },
  ].filter(d => d.value > 0);

  return data.length > 0 ? data : [{ type: 'empty', value: 1 }];
});

const chartSvg = ref(null);

watchEffect(() => {
  if (chartSvg.value) {
    drawPieChart(chartSvg.value, pieData.value);
  }
});

</script>

<style scoped>
.pie-chart-container {
  width: 100%;
  max-width: 380px;
  margin: 0 auto;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.pie-chart-container:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 4px;
}

.region-title {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--vp-c-brand);
  /* 居中 */
  text-align: center;
  width: 100%;
}
</style>