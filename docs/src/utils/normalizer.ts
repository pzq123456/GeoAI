/**
 * 创建数值归一化映射函数，支持多种拉伸模式
 * @param data - GeoJSON的features数组
 * @param column - 要归一化的属性列名（如"Year2014"）
 * @param options - 配置选项
 * @returns 接收原始值返回0-1之间的归一化值的函数
 */
export function createNormalizer(
    data: Array<{ properties?: Record<string, any> }>,
    column: string,
    options: {
        mode?: 'linear' | 'log' | 'sqrt' | 'exp' | 'arctan',
        epsilon?: number,
        boundaryEpsilon?: number,
        expBase?: number
    } = {}
): (value: number) => number {
    // 默认配置
    let {
        mode = 'linear',
        epsilon = 1e-10,
        boundaryEpsilon = 1e-5,
        expBase = 2
    } = options;

    // 验证输入
    if (!Array.isArray(data) || !column || typeof column !== 'string') {
        return () => NaN;
    }

    // 验证拉伸模式
    const validModes = ['linear', 'log', 'sqrt', 'exp', 'arctan'] as const;
    let selectedMode = mode;
    if (!validModes.includes(mode as any)) {
        console.warn(`Invalid mode: ${mode}. Falling back to 'linear'.`);
        selectedMode = 'linear';
    }

    // 验证boundaryEpsilon
    if (typeof boundaryEpsilon !== 'number' || boundaryEpsilon <= 0 || boundaryEpsilon >= 0.5) {
        console.warn(`Invalid boundaryEpsilon: ${boundaryEpsilon}. Using default 1e-5.`);
        boundaryEpsilon = 1e-5;
    }

    // 第一阶段：计算最小最大值
    let min = Infinity;
    let max = -Infinity;
    let hasValidValue = false;

    for (const feature of data) {
        if (!feature?.properties) continue;

        const value = feature.properties[column];
        if (typeof value === 'number' && !isNaN(value) && value !== null) {
            min = Math.min(min, value);
            max = Math.max(max, value);
            hasValidValue = true;
        }
    }

    // 处理无有效数值
    if (!hasValidValue) {
        return () => NaN;
    }

    // 处理所有值相同的情况
    if (min === max) {
        return () => 0.5;
    }

    // 对数、平方根、指数模式需要正值域
    if (['log', 'sqrt', 'exp'].includes(selectedMode)) {
        if (min < 0) {
            console.warn(`Negative values detected (min: ${min}). Shifting data to positive range for ${selectedMode} mode.`);
            const shift = -min + epsilon;
            min += shift;
            max += shift;
        } else if (min === 0 && selectedMode === 'log') {
            min = epsilon;
        }
    }

    const range = max - min;

    // 第二阶段：返回归一化函数
    return function normalize(value: number): number {
        if (typeof value !== 'number' || isNaN(value) || value === null) {
            return NaN;
        }

        let normalized: number;
        switch (selectedMode) {
            case 'linear':
                normalized = (value - min) / range;
                break;
            case 'log':
                normalized = Math.log(value - min + epsilon) / Math.log(max - min + epsilon);
                break;
            case 'sqrt':
                normalized = Math.sqrt(value - min) / Math.sqrt(max - min);
                break;
            case 'exp':
                normalized = (Math.pow(expBase, value - min) - 1) / (Math.pow(expBase, max - min) - 1);
                break;
            case 'arctan':
                normalized = Math.atan(value - min) / Math.atan(max - min);
                break;
            default:
                normalized = (value - min) / range;
        }

        const clamped = Math.max(0, Math.min(1, normalized));
        return boundaryEpsilon + (1 - 2 * boundaryEpsilon) * clamped;
    };
}