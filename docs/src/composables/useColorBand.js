import * as d3 from 'd3';
import { scaleOrdinal, scaleSequential, scaleDiverging } from 'd3-scale';

/**
 * 创建颜色映射函数工厂
 * @param {Object} options 配置选项
 * @param {string} [options.type='sequential'] 色带类型 'ordinal'|'sequential'|'diverging'
 * @param {string|Array} [options.scheme='viridis'] 色板名称或自定义颜色数组
 * @param {Array} [options.domain] 值域范围 [min, max] 或离散值数组
 * @param {boolean} [options.isReverse=false] 是否反转色带
 * @returns {Function} 颜色映射函数 (value: number) => string
 */
export function createColorBand({
  type = 'sequential',
  scheme = 'ylorrd',
  domain,
  isReverse = false,
} = {}) {
  let scale;

  if (type === 'ordinal') {
    const range = typeof scheme === 'string'
      ? getPredefinedOrdinalScheme(scheme)
      : (Array.isArray(scheme) ? scheme : ['#cccccc']); // Fallback for invalid scheme

    // 处理离散色带反转
    const finalRange = isReverse ? [...range].reverse() : range;
    scale = scaleOrdinal().range(finalRange);
  } else {
    const interpolator = typeof scheme === 'string'
      ? getPredefinedInterpolator(scheme)
      : (Array.isArray(scheme) ? d3.interpolateRgbBasis(scheme) : d3.interpolateViridis); // Fallback

    // 处理连续或发散色带反转
    const finalInterpolator = isReverse
      ? (t) => interpolator(1 - t)
      : interpolator;

    if (type === 'diverging') {
      scale = scaleDiverging().interpolator(finalInterpolator);
    } else {
      scale = scaleSequential().interpolator(finalInterpolator);
    }
  }

  if (domain && Array.isArray(domain)) {
    scale.domain(domain);
  } else if (type === 'diverging' && !domain) {
    // Default domain for diverging scales to ensure proper behavior
    scale.domain([-1, 0, 1]);
  } else if (type === 'sequential' && !domain) {
    // Default domain for sequential scales
    scale.domain([0, 1]);
  }

  return scale;
}

/**
 * 获取预定义的离散色板
 */
export function getPredefinedOrdinalScheme(schemeName) {
  if (typeof schemeName !== 'string') {
    return d3.schemeCategory10;
  }

  const schemeMap = {
    'category10': d3.schemeCategory10,
    'accent': d3.schemeAccent,
    'dark2': d3.schemeDark2,
    'paired': d3.schemePaired,
    'pastel1': d3.schemePastel1,
    'pastel2': d3.schemePastel2,
    'set1': d3.schemeSet1,
    'set2': d3.schemeSet2,
    'set3': d3.schemeSet3,
    'tableau10': d3.schemeTableau10,
  };

  return schemeMap[schemeName.toLowerCase()] || d3.schemeCategory10;
}

/**
 * 获取预定义的连续/发散插值器
 */
export function getPredefinedInterpolator(schemeName) {
  if (typeof schemeName !== 'string') {
    return d3.interpolateViridis;
  }

  const interpolatorMap = {
    // 连续色板
    'viridis': d3.interpolateViridis,
    'plasma': d3.interpolatePlasma,
    'inferno': d3.interpolateInferno,
    'magma': d3.interpolateMagma,
    'cividis': d3.interpolateCividis,
    'turbo': d3.interpolateTurbo,
    'ylorrd': d3.interpolateYlOrRd, // Consistent casing

    // 发散色板
    'spectral': d3.interpolateSpectral,
    'rdbu': d3.interpolateRdBu,
    'rdylbu': d3.interpolateRdYlBu,
    'rdylgn': d3.interpolateRdYlGn,
    'piyg': d3.interpolatePiYG,
    'prgn': d3.interpolatePRGn,
    'brbg': d3.interpolateBrBG,
  };

  return interpolatorMap[schemeName.toLowerCase()] || d3.interpolateViridis;
}

/**
 * 反转色带方案
 * @param {string|Array} scheme 色带名称或自定义颜色数组
 * @param {string} type 色带类型 ('ordinal'|'sequential'|'diverging')
 * @returns {Array|Function} 反转后的色带
 */
export function reverseScheme(scheme, type) {
  if (typeof scheme !== 'string') {
    // 自定义颜色数组直接反转
    return Array.isArray(scheme) ? [...scheme].reverse() : ['#cccccc'];
  }

  // 处理预定义色板的反转
  if (type === 'ordinal') {
    const colors = getPredefinedOrdinalScheme(scheme);
    return [...colors].reverse();
  } else {
    return scheme; // Interpolator reversal handled in createColorBand
  }
}

// 色带分组配置
export const colorSchemes = [
  {
    label: 'continuous',
    options: [
      { value: 'viridis', label: 'Viridis', type: 'sequential' },
      { value: 'plasma', label: 'Plasma', type: 'sequential' },
      { value: 'inferno', label: 'Inferno', type: 'sequential' },
      { value: 'magma', label: 'Magma', type: 'sequential' },
      { value: 'cividis', label: 'Cividis', type: 'sequential' },
      { value: 'turbo', label: 'Turbo', type: 'sequential' },
    ],
  },
  {
    label: 'diverging',
    options: [
      { value: 'spectral', label: 'Spectral', type: 'diverging' },
      { value: 'ylorrd', label: 'Yellow-Orange-Red', type: 'diverging' }, // Consistent casing
      { value: 'rdbu', label: 'Red-Blue', type: 'diverging' },
      { value: 'rdylbu', label: 'Red-Yellow-Blue', type: 'diverging' },
      { value: 'rdylgn', label: 'Red-Yellow-Green', type: 'diverging' },
      { value: 'piyg', label: 'Pink-Yellow-Green', type: 'diverging' },
    ],
  },
  {
    label: 'discrete',
    options: [
      { value: 'category10', label: 'Category10', type: 'ordinal' },
      { value: 'accent', label: 'Accent', type: 'ordinal' },
      { value: 'set1', label: 'Set1', type: 'ordinal' },
      { value: 'set2', label: 'Set2', type: 'ordinal' },
      { value: 'set3', label: 'Set3', type: 'ordinal' },
      { value: 'pastel1', label: 'Pastel1', type: 'ordinal' },
    ],
  },
];


// composables/useColorBand.js
import { ref, computed } from 'vue'

export function useColorBand(initialScheme = 'ylorrd', initialDomain = [0, 1]) {
  // 状态
  const selectedScheme = ref(initialScheme)
  const isReverse = ref(false)
  const currentColorBand = ref(null)
  const domain = ref(initialDomain)
  
  // 计算属性
  const colorSchemeGroups = colorSchemes
  
  const currentSchemeConfig = computed(() => {
    for (const group of colorSchemeGroups) {
      const found = group.options.find((s) => s.value === selectedScheme.value)
      if (found) return found
    }
    return colorSchemeGroups[0].options[0]
  })

  // 方法
  function getPreviewBackground(scheme) {
    const type = scheme?.type || currentSchemeConfig.value.type
    const isOrdinal = type === 'ordinal'

    if (isOrdinal) {
      const colors =
        typeof scheme.value === 'string'
          ? getPredefinedOrdinalScheme(scheme.value) || ['#cccccc']
          : scheme.value || ['#cccccc']
      const finalColors = isReverse.value ? [...colors].reverse() : colors
      return `linear-gradient(to right, ${finalColors.join(', ')})`
    } else {
      const interpolator =
        getPredefinedInterpolator(scheme.value) || ((t) => '#cccccc')
      const steps = 10
      const colorStops = Array.from({ length: steps }, (_, i) => {
        const t = isReverse.value ? 1 - i / (steps - 1) : i / (steps - 1)
        return interpolator(t)
      })
      return `linear-gradient(to right, ${colorStops.join(', ')})`
    }
  }

  function getSelectedPreviewBackground() {
    return getPreviewBackground(currentSchemeConfig.value)
  }

  function updateColorBand() {
    const config = currentSchemeConfig.value

    currentColorBand.value = createColorBand({
      type: config.type,
      scheme: selectedScheme.value,
      domain: domain.value,
      isReverse: isReverse.value
    })
  }

  function setDomain(newDomain) {
    domain.value = newDomain
    updateColorBand()
  }

  function setScheme(scheme) {
    selectedScheme.value = scheme
    updateColorBand()
  }

  function toggleReverse() {
    isReverse.value = !isReverse.value
    updateColorBand()
  }

  // 初始化
  updateColorBand()

  return {
    // 状态
    selectedScheme,
    isReverse,
    currentColorBand,
    domain,
    
    // 计算属性
    colorSchemeGroups,
    currentSchemeConfig,
    
    // 方法
    getPreviewBackground,
    getSelectedPreviewBackground,
    updateColorBand,
    setDomain,
    setScheme,
    toggleReverse
  }
}