<template>
  <div v-if="points.length" class="chart-wrap price-history-chart">
    <Line :data="chartData" :options="options" />
  </div>
  <div v-else class="chart-empty">Steam 가격 추이 데이터가 아직 없습니다.</div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import { CategoryScale, Chart as ChartJS, LinearScale, LineElement, PointElement, Tooltip } from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip)

const props = defineProps({ history: { type: Array, default: () => [] } })

const money = (value) => {
  const price = Number(value || 0)
  return price <= 0 ? '무료' : `₩${price.toLocaleString('ko-KR')}`
}

const axisMoney = (value) => `₩${Number(value || 0).toLocaleString('ko-KR')}`
const tooltipOrder = ['정가', '할인가', '역대 최저가']
const todayEnd = new Date()
todayEnd.setHours(23, 59, 59, 999)

const points = computed(() =>
  props.history
    .map((point) => ({
      x: Date.parse(point.recorded_at),
      y: Number(point.price || 0),
      original: Number(point.original_price || point.price || 0),
    }))
    .filter((point) => Number.isFinite(point.x) && point.x <= todayEnd.getTime())
    .sort((a, b) => a.x - b.x),
)

const maxValue = computed(() =>
  points.value.length ? Math.max(...points.value.map((point) => Math.max(point.original, point.y))) : 0,
)

const minValue = computed(() => (points.value.length ? Math.min(...points.value.map((point) => point.y)) : 0))
const firstDate = computed(() => points.value[0]?.x)
const lastDate = computed(() => points.value[points.value.length - 1]?.x)

const chartData = computed(() => ({
  datasets: [
    {
      label: '할인가',
      data: points.value.map((point) => ({ x: point.x, y: point.y })),
      borderColor: '#ff1834',
      backgroundColor: '#ff1834',
      stepped: 'before',
      tension: 0,
      pointRadius: 0,
      pointHoverRadius: 4,
      pointHitRadius: 12,
      borderWidth: 2,
    },
    {
      label: '정가',
      data: points.value.map((point) => ({ x: point.x, y: point.original })),
      borderColor: '#8d8d8c',
      backgroundColor: '#8d8d8c',
      borderDash: [4, 5],
      stepped: 'before',
      tension: 0,
      pointRadius: 0,
      pointHoverRadius: 4,
      pointHitRadius: 12,
      borderWidth: 1,
    },
    {
      label: '역대 최저가',
      data: points.value.map((point) => ({ x: point.x, y: minValue.value })),
      borderColor: '#24d481',
      backgroundColor: '#24d481',
      borderDash: [4, 5],
      tension: 0,
      pointRadius: 0,
      pointHoverRadius: 0,
      pointHitRadius: 0,
      borderWidth: 1.5,
    },
  ],
}))

const formatDate = (value) =>
  new Intl.DateTimeFormat('ko-KR', { month: '2-digit', day: '2-digit' }).format(new Date(value))

const options = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  parsing: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      displayColors: true,
      mode: 'index',
      intersect: false,
      backgroundColor: '#252525',
      borderColor: '#333333',
      borderWidth: 1,
      titleColor: '#ffffff',
      bodyColor: '#d9d9d8',
      bodySpacing: 6,
      padding: 10,
      itemSort: (a, b) => tooltipOrder.indexOf(a.dataset.label) - tooltipOrder.indexOf(b.dataset.label),
      callbacks: {
        title: (items) =>
          new Intl.DateTimeFormat('ko-KR', { month: 'numeric', day: 'numeric' }).format(new Date(items[0].parsed.x)),
        label: (item) => `${item.dataset.label}: ${money(item.parsed.y)}`,
      },
    },
  },
  scales: {
    x: {
      type: 'linear',
      min: firstDate.value,
      max: lastDate.value,
      border: { display: false },
      ticks: { color: '#8d8d8c', callback: formatDate, font: { size: 11, weight: 700 }, maxTicksLimit: 5 },
      grid: { color: 'rgba(217, 217, 216, 0.06)', drawTicks: false },
    },
    y: {
      min: 0,
      suggestedMax: maxValue.value * 1.08,
      border: { display: false },
      ticks: { color: '#8d8d8c', callback: axisMoney, font: { size: 11, weight: 700 }, maxTicksLimit: 4 },
      grid: { color: 'rgba(217, 217, 216, 0.06)', drawTicks: false },
    },
  },
  interaction: {
    mode: 'index',
    intersect: false,
    axis: 'x',
  },
}))
</script>
