import * as d3 from 'd3';

export function drawPieChart(svgRef, data) {
  if (!data || !svgRef) return;

  d3.select(svgRef).selectAll('*').remove();

  const width = 280;
  const height = 200;
  const margin = 24; // 增加边距
  const radius = Math.min(width, height) / 2 - margin;

  const svg = d3
    .select(svgRef)
    .attr('width', '100%')
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .append('g')
    .attr('transform', `translate(${width / 2},${height / 2 + 10})`); // 下移一点更居中

  const color = d3
    .scaleOrdinal()
    .domain(['dc', 'l1', 'l2', 'empty'])
    .range(['teal', '#682487', '#84BA42', '#d1d5db']);

  const pie = d3
    .pie()
    .value(d => d.value)
    .sort(null);

  const arc = d3
    .arc()
    .innerRadius(radius * 0.55) // 设置内半径，做成环形图
    .outerRadius(radius);

  const arcs = svg
    .selectAll('.arc')
    .data(pie(data))
    .enter()
    .append('g')
    .attr('class', 'arc');

  arcs
    .append('path')
    .attr('d', arc)
    .attr('fill', d => color(d.data.type))
    .attr('stroke', d => d3.color(color(d.data.type)).darker())
    .attr('stroke-width', 1)
    .on('mouseover', function (event, d) {
      d3.select(this).attr('opacity', 0.8);
      const type = d.data.type === 'empty' ? 'no data' : d.data.type.toUpperCase();
      const percentage = (d.data.value * 100).toFixed(2);
      // tooltip 显示在鼠标附近
      svg
        .append('text')
        .attr('class', 'tooltip')
        .attr('x', arc.centroid(d)[0])
        .attr('y', arc.centroid(d)[1])
        .attr('text-anchor', 'middle')
        .attr('dy', '-0.7em')
        .style('font-size', '18px')
        .style('pointer-events', 'none')
        .style('fill', '#106a90ff') // 适应暗黑模式
        .text(d.data.type === 'empty' ? 'no data' : `${type}: ${percentage}%`);
    })
    .on('mouseout', function () {
      d3.select(this).attr('opacity', 1);
      svg.selectAll('.tooltip').remove();
    });

  // 标题
  d3.select(svgRef)
    .append('text')
    .attr('x', width / 2)
    .attr('y', height / 2 - radius - 10) // 调整标题位置
    .attr('text-anchor', 'middle')
    .style('font-size', '14px')
    .style('font-weight', 'bold')
    .style('fill', 'var(--vp-c-text-1)') // 使用主题颜色
    .text(data[0]?.type === 'empty' ? 'No Data' : 'Charging Station Type Distribution');
}