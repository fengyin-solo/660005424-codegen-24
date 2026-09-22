/**
 * 普通模式与大屏模式共用的 ECharts 配置工厂。
 * 两种模式复用同一份 series 名称、颜色与图例样式，保证切换模式后
 * 标题与图例一致，不因为大屏而出现另一套口径的展示。
 */
import type { AnomalyScore, TimeWindow } from '@/types'

export const CHART_COLORS = {
  sigma: '#f97316',
  iqr: '#a78bfa',
  trend: '#38bdf8',
  avg: '#f97316',
  axis: '#94a3b8',
}

/** 异常分数（3-sigma + IQR）—— 与普通模式完全相同的两条线与图例 */
export function anomalyOption(anoms: AnomalyScore[]) {
  return {
    backgroundColor: 'transparent',
    grid: { left: 40, right: 15, top: 28, bottom: 25 },
    legend: { right: 0, top: 0, textStyle: { color: CHART_COLORS.axis, fontSize: 10 },
      data: ['3-sigma', 'IQR'] },
    xAxis: { type: 'category' as const, data: anoms.map(a => 'W' + a.windowIndex),
      axisLabel: { color: CHART_COLORS.axis, fontSize: 9 } },
    yAxis: { type: 'value' as const, axisLabel: { color: CHART_COLORS.axis } },
    series: [
      { name: '3-sigma', type: 'line' as const, data: anoms.map(a => a.sigmaScore),
        itemStyle: { color: CHART_COLORS.sigma }, lineStyle: { width: 1.5 } },
      { name: 'IQR', type: 'line' as const, data: anoms.map(a => a.iqrScore),
        itemStyle: { color: CHART_COLORS.iqr }, lineStyle: { width: 1.5 } },
    ],
    animation: false,
  }
}

/** 窗口日志量趋势（柱状 + 均值虚线，图例：avg） */
export function trendOption(ws: TimeWindow[]) {
  return {
    backgroundColor: 'transparent',
    grid: { left: 40, right: 15, top: 28, bottom: 25 },
    legend: { right: 0, top: 0, textStyle: { color: CHART_COLORS.axis, fontSize: 10 },
      data: ['窗口日志量', 'avg'] },
    xAxis: { type: 'category' as const, data: ws.map((_, i) => 'W' + i),
      axisLabel: { color: CHART_COLORS.axis, fontSize: 9 } },
    yAxis: { type: 'value' as const, axisLabel: { color: CHART_COLORS.axis } },
    series: [{
      name: '窗口日志量', type: 'bar' as const, data: ws.map(w => w.count),
      itemStyle: { color: CHART_COLORS.trend },
      markLine: { name: 'avg', data: [{ type: 'average' as const, name: 'avg' }],
        lineStyle: { color: CHART_COLORS.avg, type: 'dashed' as const },
        label: { color: CHART_COLORS.avg } },
    }],
    animation: false,
  }
}

/** 日志级别热力图：固定 INFO/WARN/ERROR/DEBUG 四个类目 */
export const HEAT_LEVELS = ['INFO', 'WARN', 'ERROR', 'DEBUG']

export function heatmapOption(ws: TimeWindow[]) {
  const levels = HEAT_LEVELS
  const data: [number, number, number][] = []
  ws.forEach((w, i) => {
    levels.forEach((lv, j) => { data.push([i, j, w.levels[lv] || 0]) })
  })
  return {
    backgroundColor: 'transparent',
    grid: { left: 60, right: 15, top: 5, bottom: 25 },
    xAxis: { type: 'category' as const, data: ws.map((_, i) => 'W' + i),
      axisLabel: { color: CHART_COLORS.axis, fontSize: 8 } },
    yAxis: { type: 'category' as const, data: levels,
      axisLabel: { color: CHART_COLORS.axis, fontSize: 9 } },
    visualMap: { min: 0, max: Math.max(...data.map(d => d[2]), 1),
      inRange: { color: ['#1e293b', '#fef08a', '#ef4444'] }, calculable: false, show: false },
    series: [{ name: '日志级别', type: 'heatmap' as const, data,
      label: { show: true, fontSize: 8, color: CHART_COLORS.axis } }],
    animation: false,
  }
}
