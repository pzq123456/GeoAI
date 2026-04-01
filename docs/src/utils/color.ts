import * as d3 from 'd3';

export function hexToRgbaArray(hex: string): [number, number, number] | null {
    const color = d3.color(hex);
    return color ? [color.r, color.g, color.b] : null;
}