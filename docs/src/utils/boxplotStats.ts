// boxplotStats.ts
/**
 * 计算箱线图所需的统计数据
 * @param data - 输入数值数组
 * @param options - 配置选项
 * @returns 包含箱线图统计数据的对象
 */
export function computeBoxplotStats(
    data: number[],
    options: {
        whiskerMultiplier?: number; // 上下须的IQR倍数
        epsilon?: number; // 数值精度
    } = {}
): {
    q1: number;
    median: number;
    q3: number;
    iqr: number;
    whiskerMin: number;
    whiskerMax: number;
    outliers: number[];
    min: number;
    max: number;
} | null {
    // 默认配置
    let {
        whiskerMultiplier = 1.5,
        epsilon = 1e-10
    } = options;

    // 验证输入
    if (!Array.isArray(data)) {
        console.warn('Invalid input: data must be an array.');
        return null;
    }

    // 过滤有效数值
    const validData = data.filter(
        (value) => typeof value === 'number' && !isNaN(value) && value !== null
    );
    if (validData.length === 0) {
        console.warn('No valid numerical data provided.');
        return null;
    }

    // 验证whiskerMultiplier
    if (typeof whiskerMultiplier !== 'number' || whiskerMultiplier <= 0) {
        console.warn(`Invalid whiskerMultiplier: ${whiskerMultiplier}. Using default 1.5.`);
        whiskerMultiplier = 1.5;
    }

    // 排序数据（副本以避免修改原数组）
    const sortedData = [...validData].sort((a, b) => a - b);
    const n = sortedData.length;

    // 计算最小值和最大值
    const min = sortedData[0];
    const max = sortedData[n - 1];

    // 计算四分位数
    const getQuantile = (q: number): number => {
        const index = q * (n - 1);
        const lowerIndex = Math.floor(index);
        const fraction = index - lowerIndex;
        if (fraction < epsilon) {
            return sortedData[lowerIndex];
        }
        return sortedData[lowerIndex] * (1 - fraction) + sortedData[lowerIndex + 1] * fraction;
    };

    const q1 = getQuantile(0.25); // 第一四分位数
    const median = getQuantile(0.5); // 中位数
    const q3 = getQuantile(0.75); // 第三四分位数
    const iqr = q3 - q1; // 四分位距

    // 计算上下须
    const whiskerMin = Math.max(min, q1 - whiskerMultiplier * iqr);
    const whiskerMax = Math.min(max, q3 + whiskerMultiplier * iqr);

    // 识别异常点
    const outliers = sortedData.filter((value) => value < whiskerMin || value > whiskerMax);

    // 返回统计结果
    return {
        q1,
        median,
        q3,
        iqr,
        whiskerMin,
        whiskerMax,
        outliers,
        min,
        max
    };
}

/**
 * 适配器函数，用于从GeoJSON features提取多列数值数据，适配箱线图统计
 * @param data - GeoJSON的features数组
 * @param options - 配置选项
 * @returns 包含每列数值数据的Map或null
 */
export function adaptGeojsonForBoxplot(
    data: Array<{ properties?: Record<string, any> }>,
    options: {
        columns?: string[] | { startYear: number; endYear: number }; // 列名或年份范围
    } = {}
): Map<string, number[]> | null {
    // 默认配置
    let { columns = { startYear: 2014, endYear: 2024 } } = options;

    // 验证输入
    if (!Array.isArray(data)) {
        console.warn('Invalid input: data must be an array of features.');
        return null;
    }

    // 处理列名
    let columnNames: string[];
    if (Array.isArray(columns)) {
        columnNames = columns;
    } else if (typeof columns === 'object' && 'startYear' in columns && 'endYear' in columns) {
        const { startYear, endYear } = columns;
        if (
            !Number.isInteger(startYear) ||
            !Number.isInteger(endYear) ||
            startYear > endYear ||
            startYear < 1900 ||
            endYear > 2100
        ) {
            console.warn('Invalid year range. Using default 2014-2024.');
            columnNames = Array.from(
                { length: 2024 - 2014 + 1 },
                (_, i) => `Year${2014 + i}`
            );
        } else {
            columnNames = Array.from(
                { length: endYear - startYear + 1 },
                (_, i) => `Year${startYear + i}`
            );
        }
    } else {
        console.warn('Invalid columns option. Using default Year2014-Year2024.');
        columnNames = Array.from({ length: 2024 - 2014 + 1 }, (_, i) => `Year${2014 + i}`);
    }

    // 验证列名
    if (columnNames.length === 0 || !columnNames.every((col) => typeof col === 'string')) {
        console.warn('Invalid column names.');
        return null;
    }

    // 提取每列数据
    const validDataCache: Map<string, number[]> = new Map();
    let hasValidData = false;

    // 遍历数据一次，收集所有列的数值
    for (const feature of data) {
        if (!feature?.properties) continue;
        for (const column of columnNames) {
            const value = feature.properties[column];
            if (typeof value === 'number' && !isNaN(value) && value !== null) {
                if (!validDataCache.has(column)) {
                    validDataCache.set(column, []);
                }
                validDataCache.get(column)!.push(value);
                hasValidData = true;
            }
        }
    }

    // 验证是否有有效数据
    if (!hasValidData) {
        console.warn('No valid data found for any column.');
        return null;
    }

    return validDataCache;
}

/**
 * 通用函数，计算多列数据的箱线图统计值
 * @param columnData - 列名到数值数组的映射
 * @param options - 配置选项
 * @returns 包含每列统计数据的数组
 */
export function computeMultiBoxplotStats(
    columnData: Map<string, number[]>,
    options: {
        whiskerMultiplier?: number; // 上下须的IQR倍数
        epsilon?: number; // 数值精度
    } = {}
): Array<{ column: string; stats: ReturnType<typeof computeBoxplotStats> }> | null {
    // 默认配置
    let {
        whiskerMultiplier = 1.5,
        epsilon = 1e-10
    } = options;

    // 验证输入
    if (!(columnData instanceof Map)) {
        console.warn('Invalid input: columnData must be a Map.');
        return null;
    }

    if (columnData.size === 0) {
        console.warn('No columns provided.');
        return null;
    }

    // 计算每列统计数据
    const results: Array<{ column: string; stats: ReturnType<typeof computeBoxplotStats> }> = [];
    let hasValidStats = false;

    for (const [column, data] of columnData) {
        const stats = computeBoxplotStats(data, { whiskerMultiplier, epsilon });
        results.push({ column, stats });
        if (stats !== null) {
            hasValidStats = true;
        }
    }

    // 验证结果
    if (!hasValidStats) {
        console.warn('No valid statistics computed for any column.');
        return null;
    }

    return results;
}

/**
 * 计算堆叠柱状图所需的占比数据
 * @param data - GeoJSON的features数组
 * @param options - 配置选项
 * @returns 包含每年各类别占比的数组
 */
export function computeStackedBarData(
  data: Array<{ properties?: Record<string, any> }>,
  options: {
    columns?: { startYear: number; endYear: number };
  } = {}
): Array<{ year: string; dc: number; l1: number; l2: number; total: number }> | null {
  // 默认年份范围
  let { columns = { startYear: 2014, endYear: 2024 } } = options;

  // 验证年份范围
  const { startYear, endYear } = columns;
  if (
    !Number.isInteger(startYear) ||
    !Number.isInteger(endYear) ||
    startYear > endYear ||
    startYear < 1900 ||
    endYear > 2100
  ) {
    console.warn('Invalid year range. Using default 2014-2024.');
    columns = { startYear: 2014, endYear: 2024 };
  }

  // 生成年份列名
  const years = Array.from(
    { length: endYear - startYear + 1 },
    (_, i) => `${startYear + i}`
  );

  // 初始化结果数组
  const result: Array<{ year: string; dc: number; l1: number; l2: number; total: number }> = [];
  let hasValidData = false;

  // 遍历每年，计算总量和占比
  for (const year of years) {
    const totalKey = `Year${year}`;
    const dcKey = `Year${year}_dc`;
    const l1Key = `Year${year}_l1`;
    const l2Key = `Year${year}_l2`;

    // 统计每年的总量和各类别值
    let totalSum = 0;
    let dcSum = 0;
    let l1Sum = 0;
    let l2Sum = 0;

    for (const feature of data) {
      if (!feature?.properties) continue;
      const total = feature.properties[totalKey];
      const dc = feature.properties[dcKey];
      const l1 = feature.properties[l1Key];
      const l2 = feature.properties[l2Key];

      if (typeof total === 'number' && !isNaN(total)) totalSum += total;
      if (typeof dc === 'number' && !isNaN(dc)) dcSum += dc;
      if (typeof l1 === 'number' && !isNaN(l1)) l1Sum += l1;
      if (typeof l2 === 'number' && !isNaN(l2)) l2Sum += l2;
    }

    // 计算占比（避免除以零）
    const total = totalSum > 0 ? totalSum : 1; // 防止除以零
    const dcRatio = dcSum / total;
    const l1Ratio = l1Sum / total;
    const l2Ratio = l2Sum / total;

    if (totalSum > 0) hasValidData = true;

    result.push({
      year,
      dc: dcRatio,
      l1: l1Ratio,
      l2: l2Ratio,
      total: totalSum,
    });
  }

  if (!hasValidData) {
    console.warn('No valid data found for any year.');
    return null;
  }

  return result;
}