<template>
  <div :style="{ width: width, height: height }" class="map-container" ref="mapContainerRef">
    <div class="map-overlay">
      <div class="map-legend-container">
        <slot name="legend"></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useData } from 'vitepress'
const { isDark } = useData();

import { onMounted, onUnmounted, watch, computed, ref } from 'vue';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

const mapContainerRef = ref(null);

const props = defineProps({
  center: {
    type: Array,
    default: () => [0.45, 51.47],
    validator: (value) => value.length === 2
  },
  zoom: {
    type: Number,
    default: 11
  },
  bearing: {
    type: Number,
    default: 0
  },
  pitch: {
    type: Number,
    default: 0
  },
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '100vh'
  },
  styleUrl: {
    type: String,
    default: null
  },
  flyToOptions: {
    type: Object,
    default: null
  },
  fitBounds: {
    type: Array,
    default: null
  },
  preserveDrawingBuffer: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['map-loaded', 'map-move', 'map-click', 'map-rendered']);

const map = ref(null);
const isMapLoaded = ref(false);

// 默认样式
const lightStyle = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';
const darkStyle = 'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json';
const defaultStyle = 'https://demotiles.maplibre.org/style.json';

const mapStyle = computed(() => {
  if (props.styleUrl) return props.styleUrl;
  return isDark.value ? darkStyle : lightStyle;
});

// 初始化地图
const initMap = () => {
  map.value = new maplibregl.Map({
    container: mapContainerRef.value,
    style: mapStyle.value,
    center: props.center,
    zoom: props.zoom,
    bearing: props.bearing,
    pitch: props.pitch,
    preserveDrawingBuffer: props.preserveDrawingBuffer,
    antialias: true, // 更好的抗锯齿效果，适合与deck.gl结合
    attributionControl: false // 禁用右下角的属性控件
  });

  // 添加常用事件监听
  map.value.on('load', () => {
    isMapLoaded.value = true;
    emit('map-loaded', map.value);
  });

  map.value.on('render', () => {
    emit('map-rendered');
  });

  map.value.on('move', () => {
    if (!map.value.isMoving()) {
      emit('map-move', {
        center: map.value.getCenter(),
        zoom: map.value.getZoom(),
        bearing: map.value.getBearing(),
        pitch: map.value.getPitch()
      });
    }
  });

  map.value.on('click', (e) => {
    emit('map-click', {
      lngLat: e.lngLat,
      point: e.point
    });
  });
};

// 响应式更新地图位置
watch(() => props.center, (newCenter) => {
  if (isMapLoaded.value && newCenter) {
    map.value.flyTo({ center: newCenter });
  }
}, { deep: true });

watch(() => props.zoom, (newZoom) => {
  if (isMapLoaded.value && newZoom !== undefined) {
    map.value.flyTo({ zoom: newZoom });
  }
});

watch(() => props.bearing, (newBearing) => {
  if (isMapLoaded.value && newBearing !== undefined) {
    map.value.flyTo({ bearing: newBearing });
  }
});

watch(() => props.pitch, (newPitch) => {
  if (isMapLoaded.value && newPitch !== undefined) {
    map.value.flyTo({ pitch: newPitch });
  }
});

watch(() => props.flyToOptions, (options) => {
  if (isMapLoaded.value && options) {
    map.value.flyTo(options);
  }
}, { deep: true });

watch(() => props.fitBounds, (bounds) => {
  if (isMapLoaded.value && bounds) {
    map.value.fitBounds(bounds, {
      padding: 20,
      duration: 1000
    });
  }
}, { deep: true });

watch(mapStyle, (newStyle) => {
  if (isMapLoaded.value) {
    map.value.setStyle(newStyle);
  }
});

onMounted(
  () => {
    initMap();
  },
);

onUnmounted(() => {
  if (map.value) {
    // 然后移除地图
    map.value.remove();
    map.value = null;
  }
});

// 暴露map实例和方法给父组件
defineExpose({
  map,
  isMapLoaded,
  flyTo: (options) => {
    if (isMapLoaded.value) {
      map.value.flyTo(options);
    }
  },
  fitBounds: (bounds, options) => {
    if (isMapLoaded.value) {
      map.value.fitBounds(bounds, options);
    }
  },
  setCenter: (center) => {
    if (isMapLoaded.value) {
      map.value.flyTo({ center });
    }
  },
  setZoom: (zoom) => {
    if (isMapLoaded.value) {
      map.value.flyTo({ zoom });
    }
  }
});
</script>

<style scoped>
.map-container {
  position: relative;
  width: 100%;
  height: 100%;
  border: 1px solid var(--vp-c-border);
}

.map-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 1;
}

.map-legend-container {
  position: absolute;
  right: 10px;
  top: 10px;
  pointer-events: auto;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 4px;
  background-color: rgba(128, 128, 128, 0.186);
  /* 模糊 */
  backdrop-filter: blur(10px);
}

</style>