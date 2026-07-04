<template>
  <section v-if="steamPrice" class="panel price-insight-panel">
    <div class="section-title price-insight-title">
      <div>
        <h2>가격 인사이트</h2>
        <span>{{ periodLabel }}</span>
      </div>
      <strong :class="['price-timing-badge', timingTone]">{{ timingLabel }}</strong>
    </div>

    <div class="price-insight-grid">
      <article>
        <span>현재가</span>
        <strong>{{ money(currentPrice) }}</strong>
      </article>
      <article>
        <span>역대 최저가</span>
        <strong>{{ money(historicalLow) }}</strong>
      </article>
      <article>
        <span>최저가 대비</span>
        <strong>{{ lowDeltaLabel }}</strong>
      </article>
      <article>
        <span>현재 할인율</span>
        <strong>{{ discountLabel }}</strong>
      </article>
    </div>

    <div class="price-position-card">
      <div class="price-position-head">
        <span>가격 위치</span>
        <strong>{{ positionSummary }}</strong>
      </div>
      <div class="price-position-track" aria-hidden="true">
        <span class="price-position-fill" :style="{ width: `${currentPosition}%` }"></span>
        <i class="price-position-marker current" :style="{ left: `${currentPosition}%` }"></i>
      </div>
      <div class="price-position-labels">
        <span>
          <small>최저</small>
          <strong>{{ money(rangeLow) }}</strong>
        </span>
        <span>
          <small>현재</small>
          <strong>{{ money(currentPrice) }}</strong>
        </span>
        <span>
          <small>정가</small>
          <strong>{{ money(rangeHigh) }}</strong>
        </span>
      </div>
    </div>

    <div class="price-insight-body">
      <article class="price-advice-card">
        <h3>구매 판단</h3>
        <p>{{ timingDescription }}</p>
      </article>

      <article class="price-pattern-card">
        <h3>할인 패턴</h3>
        <div class="price-pattern-stats">
          <span>
            <small>할인 기록</small>
            <strong>{{ discountEventCount }}회</strong>
          </span>
          <span>
            <small>평균 간격</small>
            <strong>{{ averageDiscountGapLabel }}</strong>
          </span>
          <span>
            <small>최대 할인</small>
            <strong>{{ maxDiscountLabel }}</strong>
          </span>
        </div>
      </article>
    </div>

    <div v-if="recentDiscountEvents.length" class="price-event-timeline">
      <h3>최근 할인 이벤트</h3>
      <ol>
        <li v-for="event in recentDiscountEvents" :key="`${event.start}-${event.end}-${event.price}-${event.discount}`">
          <span>{{ eventPeriod(event) }}</span>
          <strong>{{ money(event.price) }}</strong>
          <em>-{{ percent(event.discount) }}</em>
        </li>
      </ol>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { money, percent } from '../utils/format'

const props = defineProps({
  game: { type: Object, default: null },
  history: { type: Array, default: () => [] },
})

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

const numberValue = (value) => {
  const number = Number(value || 0)
  return Number.isFinite(number) ? number : 0
}

const formatDate = (value) => {
  if (!value) return ''
  return new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value))
}

const daysBetween = (from, to) => {
  const start = Date.parse(from)
  const end = Date.parse(to)
  if (!Number.isFinite(start) || !Number.isFinite(end)) return 0
  return Math.round((end - start) / 86400000)
}

const steamPrice = computed(
  () =>
    props.game?.prices?.find((price) => price.store?.name?.toLowerCase() === 'steam') ||
    props.game?.prices?.[0] ||
    null,
)

const historyPoints = computed(() =>
  [...props.history]
    .filter((point) => numberValue(point.price) > 0 && point.recorded_at)
    .sort((a, b) => Date.parse(a.recorded_at) - Date.parse(b.recorded_at)),
)

const currentPrice = computed(() => numberValue(steamPrice.value?.current_price))
const originalPrice = computed(() => numberValue(steamPrice.value?.original_price))
const currentDiscount = computed(() => {
  const explicit = numberValue(steamPrice.value?.discount_rate)
  if (explicit) return explicit
  if (originalPrice.value > currentPrice.value && currentPrice.value > 0) {
    return Math.round((1 - currentPrice.value / originalPrice.value) * 100)
  }
  return 0
})

const historicalLow = computed(() => {
  const candidates = [
    numberValue(steamPrice.value?.historical_low_price),
    ...historyPoints.value.map((point) => numberValue(point.price)),
    currentPrice.value,
  ].filter((value) => value > 0)
  return candidates.length ? Math.min(...candidates) : 0
})

const hasHistoricalReference = computed(
  () => numberValue(steamPrice.value?.historical_low_price) > 0 || historyPoints.value.length > 0,
)

const rangeHigh = computed(() => {
  const candidates = [
    originalPrice.value,
    currentPrice.value,
    ...historyPoints.value.map((point) => Math.max(numberValue(point.original_price), numberValue(point.price))),
  ].filter((value) => value > 0)
  return candidates.length ? Math.max(...candidates) : currentPrice.value
})

const rangeLow = computed(() => historicalLow.value || currentPrice.value)

const currentPosition = computed(() => {
  if (!rangeHigh.value || rangeHigh.value <= rangeLow.value) return 0
  return clamp(Math.round(((currentPrice.value - rangeLow.value) / (rangeHigh.value - rangeLow.value)) * 100), 0, 100)
})

const lowDelta = computed(() => Math.max(0, currentPrice.value - historicalLow.value))
const lowDeltaPercent = computed(() => (historicalLow.value ? (lowDelta.value / historicalLow.value) * 100 : 0))

const lowDeltaLabel = computed(() => {
  if (!historicalLow.value) return '-'
  if (lowDelta.value <= 0) return '동일'
  return `+${money(lowDelta.value)}`
})

const discountLabel = computed(() => (currentDiscount.value > 0 ? `-${percent(currentDiscount.value)}` : '할인 없음'))

const periodLabel = computed(() => {
  if (!historyPoints.value.length) return '가격 기록 준비 중'
  return `${formatDate(historyPoints.value[0].recorded_at)} - ${formatDate(historyPoints.value.at(-1).recorded_at)}`
})

const timingTone = computed(() => {
  if (!hasHistoricalReference.value) return currentDiscount.value > 0 ? 'sale' : 'neutral'
  if (historicalLow.value && currentPrice.value <= historicalLow.value) return 'best'
  if (historicalLow.value && lowDeltaPercent.value <= 5) return 'near'
  if (currentDiscount.value >= 50) return 'deal'
  if (currentDiscount.value > 0) return 'sale'
  return 'neutral'
})

const timingLabel = computed(() => {
  if (timingTone.value === 'best') return '역대 최저가'
  if (timingTone.value === 'near') return '최저가 근접'
  if (timingTone.value === 'deal') return '강한 할인'
  if (timingTone.value === 'sale') return '할인 중'
  return '할인 없음'
})

const timingDescription = computed(() => {
  if (!hasHistoricalReference.value && currentDiscount.value > 0) {
    return '현재 할인 중이지만 저장된 가격 이력이 아직 부족해 최저가 여부는 더 지켜봐야 합니다.'
  }
  if (!hasHistoricalReference.value) return '저장된 가격 이력이 아직 부족해 현재가와 할인율 중심으로 확인해 주세요.'
  if (timingTone.value === 'best') return '현재 가격이 저장된 가격 기록의 최저가와 같습니다.'
  if (timingTone.value === 'near') {
    return `역대 최저가보다 약 ${Math.round(lowDeltaPercent.value)}% 높아 최저가에 가까운 편입니다.`
  }
  if (currentDiscount.value > 0 && originalPrice.value > currentPrice.value) {
    return `정가보다 ${money(originalPrice.value - currentPrice.value)} 저렴하지만, 최저가와의 차이도 함께 확인하는 편이 좋습니다.`
  }
  return '현재는 할인 정보가 없어 정가 대비 가격 메리트가 크지 않은 상태입니다.'
})

const positionSummary = computed(() => {
  if (!historicalLow.value || !rangeHigh.value) return '가격 기준 부족'
  if (currentPrice.value <= historicalLow.value) return '최저 구간'
  if (currentPosition.value <= 20) return '낮은 가격대'
  if (currentPosition.value <= 55) return '중간 가격대'
  return '높은 가격대'
})

const discountEvents = computed(() => {
  const events = []
  let currentEvent = null
  for (const point of historyPoints.value) {
    const discount = numberValue(point.discount_rate)
    if (discount <= 0) {
      currentEvent = null
      continue
    }
    const price = numberValue(point.price)
    const shouldExtend =
      currentEvent &&
      currentEvent.discount === discount &&
      currentEvent.price === price &&
      daysBetween(currentEvent.end, point.recorded_at) <= 3

    if (shouldExtend) {
      currentEvent.end = point.recorded_at
      continue
    }

    currentEvent = { start: point.recorded_at, end: point.recorded_at, price, discount }
    events.push(currentEvent)
  }
  return events
})

const recentDiscountEvents = computed(() => discountEvents.value.slice(-5).reverse())
const discountEventCount = computed(() => discountEvents.value.length)
const maxDiscount = computed(() =>
  Math.max(currentDiscount.value, ...historyPoints.value.map((point) => numberValue(point.discount_rate)), 0),
)
const maxDiscountLabel = computed(() => (maxDiscount.value ? `-${percent(maxDiscount.value)}` : '-'))

const averageDiscountGap = computed(() => {
  if (discountEvents.value.length < 2) return 0
  const intervals = []
  for (let index = 1; index < discountEvents.value.length; index += 1) {
    const gap = daysBetween(discountEvents.value[index - 1].start, discountEvents.value[index].start)
    if (gap > 0) intervals.push(gap)
  }
  if (!intervals.length) return 0
  return Math.round(intervals.reduce((sum, value) => sum + value, 0) / intervals.length)
})

const averageDiscountGapLabel = computed(() => (averageDiscountGap.value ? `${averageDiscountGap.value}일` : '-'))

const eventPeriod = (event) => {
  if (event.start === event.end) return formatDate(event.start)
  return `${formatDate(event.start)} - ${formatDate(event.end)}`
}
</script>

<style scoped>
.price-insight-panel {
  display: grid;
  gap: 18px;
  padding: 22px;
}

.price-insight-title {
  align-items: start;
}

.price-insight-title > div {
  display: grid;
  gap: 5px;
}

.price-insight-title span {
  color: #9fb3c8;
  font-size: 13px;
}

.price-timing-badge {
  border: 1px solid #33516e;
  border-radius: 999px;
  color: #d9d9d8;
  padding: 8px 12px;
  font-size: 13px;
  line-height: 1;
  white-space: nowrap;
}

.price-timing-badge.best,
.price-timing-badge.near {
  border-color: rgba(255, 24, 52, 0.54);
  background: rgba(255, 24, 52, 0.12);
  color: #ffb5bf;
}

.price-timing-badge.deal,
.price-timing-badge.sale {
  border-color: rgba(53, 213, 200, 0.46);
  background: rgba(53, 213, 200, 0.12);
  color: #a6f3df;
}

.price-insight-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.price-insight-grid article,
.price-position-card,
.price-advice-card,
.price-pattern-card,
.price-event-timeline {
  border: 1px solid #17334d;
  background: rgba(8, 19, 32, 0.62);
}

.price-insight-grid article {
  display: grid;
  gap: 7px;
  min-width: 0;
  padding: 14px;
}

.price-insight-grid span,
.price-position-head span,
.price-pattern-stats small,
.price-position-labels small {
  color: #9fb3c8;
  font-size: 12px;
  font-weight: 800;
}

.price-insight-grid strong,
.price-position-head strong,
.price-pattern-stats strong,
.price-position-labels strong {
  min-width: 0;
  color: #ffffff;
  font-size: 18px;
  font-weight: 900;
}

.price-position-card {
  display: grid;
  gap: 13px;
  padding: 16px;
}

.price-position-head,
.price-position-labels {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.price-position-track {
  position: relative;
  height: 12px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(255, 24, 52, 0.18), rgba(53, 213, 200, 0.16), rgba(217, 217, 216, 0.12));
}

.price-position-fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: inherit;
  background: linear-gradient(90deg, #ff1834, #35d5c8);
}

.price-position-marker {
  position: absolute;
  top: 50%;
  width: 18px;
  height: 18px;
  border: 3px solid #ffffff;
  border-radius: 50%;
  background: #ff1834;
  transform: translate(-50%, -50%);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
}

.price-position-labels span {
  display: grid;
  gap: 4px;
}

.price-position-labels span:nth-child(2) {
  justify-items: center;
}

.price-position-labels span:last-child {
  justify-items: end;
}

.price-insight-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr);
  gap: 12px;
}

.price-advice-card,
.price-pattern-card {
  display: grid;
  gap: 10px;
  align-content: start;
  padding: 16px;
}

.price-advice-card h3,
.price-pattern-card h3,
.price-event-timeline h3 {
  margin: 0;
  color: #ffffff;
  font-size: 15px;
}

.price-advice-card p {
  margin: 0;
  color: #c7d6e5;
  line-height: 1.6;
}

.price-pattern-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.price-pattern-stats span {
  display: grid;
  gap: 5px;
}

.price-event-timeline {
  display: grid;
  gap: 12px;
  padding: 16px;
}

.price-event-timeline ol {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.price-event-timeline li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 10px;
  align-items: center;
  border-top: 1px solid rgba(159, 179, 200, 0.18);
  padding-top: 8px;
}

.price-event-timeline li:first-child {
  border-top: 0;
  padding-top: 0;
}

.price-event-timeline li span {
  min-width: 0;
  overflow: hidden;
  color: #c7d6e5;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.price-event-timeline li strong {
  color: #ffffff;
}

.price-event-timeline li em {
  border-radius: 4px;
  background: #ff1834;
  color: #ffffff;
  padding: 4px 7px;
  font-size: 12px;
  font-style: normal;
  font-weight: 900;
  line-height: 1;
}

:global(:root[data-theme="light"]) .price-insight-title span,
:global(:root[data-theme="light"]) .price-insight-grid span,
:global(:root[data-theme="light"]) .price-position-head span,
:global(:root[data-theme="light"]) .price-pattern-stats small,
:global(:root[data-theme="light"]) .price-position-labels small {
  color: #5f7185;
}

:global(:root[data-theme="light"]) .price-insight-grid article,
:global(:root[data-theme="light"]) .price-position-card,
:global(:root[data-theme="light"]) .price-advice-card,
:global(:root[data-theme="light"]) .price-pattern-card,
:global(:root[data-theme="light"]) .price-event-timeline {
  border-color: rgba(20, 25, 35, 0.12);
  background: #ffffff;
}

:global(:root[data-theme="light"]) .price-insight-grid strong,
:global(:root[data-theme="light"]) .price-position-head strong,
:global(:root[data-theme="light"]) .price-pattern-stats strong,
:global(:root[data-theme="light"]) .price-position-labels strong,
:global(:root[data-theme="light"]) .price-advice-card h3,
:global(:root[data-theme="light"]) .price-pattern-card h3,
:global(:root[data-theme="light"]) .price-event-timeline h3,
:global(:root[data-theme="light"]) .price-event-timeline li strong {
  color: #111827;
}

:global(:root[data-theme="light"]) .price-advice-card p,
:global(:root[data-theme="light"]) .price-event-timeline li span {
  color: #4b5563;
}

@media (max-width: 760px) {
  .price-insight-grid,
  .price-insight-body,
  .price-pattern-stats {
    grid-template-columns: 1fr;
  }

  .price-position-labels {
    align-items: flex-start;
  }

  .price-position-labels strong {
    font-size: 14px;
  }

  .price-event-timeline li {
    grid-template-columns: 1fr;
    justify-items: start;
  }
}
</style>
