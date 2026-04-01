<template>
    <div class="chart-card">
        <slot></slot>
        <div v-if="showData" class="data-section">
            <div class="main-stats">
                <div class="stat-item">
                    <div class="stat-label">Total Value</div>
                    <div class="stat-value">{{ formatNumber(totalValue) }}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Rank</div>
                    <div class="stat-value">#{{ rankValue }}</div>
                </div>
            </div>
            
            <div class="detail-stats">
                <div class="detail-item">
                    <div class="color-indicator dc"></div>
                    <div class="detail-label">DC</div>
                    <div class="detail-value">{{ formatNumber(dcValue) }}</div>
                </div>
                <div class="detail-item">
                    <div class="color-indicator l1"></div>
                    <div class="detail-label">L1</div>
                    <div class="detail-value">{{ formatNumber(l1Value) }}</div>
                </div>
                <div class="detail-item">
                    <div class="color-indicator l2"></div>
                    <div class="detail-label">L2</div>
                    <div class="detail-value">{{ formatNumber(l2Value) }}</div>
                </div>
            </div>
        </div>
        <div v-else class="empty-state">
            <div class="empty-message">No data available</div>
        </div>
    </div>
</template>

<script setup>
import { computed } from 'vue';
import { useYearStore } from '@/stores/yearStore';
import { storeToRefs } from 'pinia';
import { useMapStore } from '@/stores/mapStore';

const yearStore = useYearStore();
const { currentYear } = storeToRefs(yearStore);

const mapStore = useMapStore();
const selectedRegion = computed(() => mapStore.selectedRegion ? mapStore.selectedRegion.properties : null);

const formatNumber = (num) => {
    return num?.toLocaleString() || '0';
};

const totalValue = computed(() => {
    if (!selectedRegion.value) return 0;
    const year = currentYear.value;
    const totalKey = `Year${year}`;
    return Number(selectedRegion.value[totalKey]) || 0;
});

const rankValue = computed(() => {
    if (!selectedRegion.value) return 0;
    const year = currentYear.value;
    const rankKey = `Rank${year}`;
    return Number(selectedRegion.value[rankKey]) || 0;
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

const showData = computed(() => {
    return selectedRegion.value && totalValue.value > 0;
});
</script>

<style scoped>
.chart-card {
    border-radius: 8px;
    padding: 16px;
    background-color: var(--vp-c-bg);
    color: var(--vp-c-text);
    border: 1px solid var(--vp-c-border);
}

.data-section {
    margin-top: 12px;
    border-top: 1px solid var(--vp-c-border);
}

.main-stats {
    display: flex;
    justify-content: space-between;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--vp-c-border);
}

.stat-item {
    text-align: center;
    flex: 1;
}

.stat-label {
    font-size: 12px;
    font-weight: 500;
    margin-bottom: 4px;
    background-color: var(--vp-c-bg-soft);
    color: var(--vp-c-text-2);
}

.stat-value {
    font-size: 18px;
    font-weight: 600;
    color: var(--vp-c-text-1);
}

.detail-stats {
    display: flex;
    justify-content: space-between;
    gap: 8px;
}

.detail-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    border-radius: 4px;
    flex: 1;
}

.color-indicator {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    flex-shrink: 0;
}

.color-indicator.dc {
    background-color: #006d5b;
    border: 1px solid #0cc2b6;
}

.color-indicator.l1 {
    background-color: #682487;
    border: 1px solid #1e40af;
}

.color-indicator.l2 {
    background-color: #84BA42;
    border: 1px solid #047857;
}

.detail-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--vp-c-text-2);
}

.detail-value {
    font-size: 13px;
    font-weight: 600;
    margin-left: auto;
    color: var(--vp-c-text-1);
    background-color: var(--vp-c-bg-soft);
}

.empty-state {
    padding: 12px 0;
    text-align: center;
}

.empty-message {
    font-size: 13px;
}
</style>