<template>
  <section class="panel score-panel" :class="{ 'is-loading': loading }">
    <div class="score-summary">
      <span class="eyebrow">{{ TEXT.eyebrow }}</span>
      <h2 v-if="loading" class="score-loading-title">
        <span>{{ TEXT.loadingTitle }}</span>
        <span class="score-loading-dots" aria-hidden="true">
          <span>.</span>
          <span>.</span>
          <span>.</span>
        </span>
      </h2>
      <h2 v-else>{{ titleText }}</h2>
      <p>{{ bodyText }}</p>
    </div>

    <div class="score-ring" :class="{ loading }" :style="scoreRingStyle">
      <svg v-if="loading" class="score-ring-loader" viewBox="0 0 112 112" aria-hidden="true">
        <circle class="score-ring-loader-track" cx="56" cy="56" r="50" />
        <circle class="score-ring-loader-arc" cx="56" cy="56" r="50" />
      </svg>
      <span v-else>{{ score }}</span>
    </div>

    <div class="score-breakdown">
      <div v-for="metric in metrics" :key="metric.label">
        <span>{{ metric.label }}</span>
        <strong class="score-metric-value" :class="{ checked: loading && metric.status === 'done' }">
          <Check v-if="loading && metric.status === 'done'" aria-hidden="true" :size="24" :stroke-width="3" />
          <span v-else-if="loading" class="score-loading-dots" aria-hidden="true">
            <span>.</span>
            <span>.</span>
            <span>.</span>
          </span>
          <template v-else>{{ metric.value }}</template>
        </strong>
      </div>
    </div>

    <div v-if="!loading && recommendation" class="score-analysis-list">
      <div v-if="recommendation.price_reason" class="analysis-block">
        <strong>{{ TEXT.priceReason }}</strong>
        <p>{{ recommendation.price_reason }}</p>
      </div>
      <div v-if="recommendation.taste_reason" class="analysis-block">
        <strong>{{ TEXT.tasteReason }}</strong>
        <p>{{ recommendation.taste_reason }}</p>
      </div>
      <div class="analysis-block">
        <strong>{{ TEXT.patternAnalysis }}</strong>
        <p>{{ recommendation.pattern_analysis }}</p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { Check } from 'lucide-vue-next'

const TEXT = {
  eyebrow: 'AI \uad6c\ub9e4 \ubd84\uc11d',
  priceReason: '\uac00\uaca9 \ud310\ub2e8',
  tasteReason: '\ucde8\ud5a5 \ud310\ub2e8',
  patternAnalysis: '\ud560\uc778 \ud328\ud134 \ubd84\uc11d',
  loadingTitle: 'AI \ubd84\uc11d\uc911',
  emptyTitle: '\uad6c\ub9e4 \ud0c0\uc774\ubc0d \ubd84\uc11d',
  loadingBody:
    '\uac00\uaca9, \uc720\uc800 \ud3c9\uac00, \ucde8\ud5a5\uc744 \ud655\uc778\ud558\uace0 AI \ubd84\uc11d \uacb0\uacfc\ub97c \uc815\ub9ac\ud558\uace0 \uc788\uc2b5\ub2c8\ub2e4.',
  buy: '\uad6c\ub9e4 \ucd94\ucc9c',
  consider: '\uc870\uac74\ubd80 \ucd94\ucc9c',
  wait: '\ub300\uae30 \ucd94\ucc9c',
  price: '\uac00\uaca9',
  taste: '\ucde8\ud5a5',
  userRating: '\uc720\uc800 \ud3c9\uac00',
}

const props = defineProps({
  recommendation: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  loadingStepItems: { type: Array, default: () => [] },
  reviewScore: { type: [Number, String], default: 0 },
})

const labels = {
  BUY: TEXT.buy,
  CONSIDER: TEXT.consider,
  WAIT: TEXT.wait,
}

const score = computed(() => Math.max(0, Math.min(100, Math.round(Number(props.recommendation?.score || 0)))))
const userReviewScore = computed(() => {
  const scoreValue = Number(props.reviewScore || props.recommendation?.quality_score || 0)
  return scoreValue ? Math.max(0, Math.min(100, Math.round(scoreValue))) : '-'
})
const metricNumber = (value, fallback = '-') => {
  const target = value ?? fallback
  if (target === '-') return target
  const number = Number(target)
  return Number.isFinite(number) ? Math.max(0, Math.min(100, Math.round(number))) : fallback
}
const titleText = computed(() => {
  if (props.loading) return TEXT.loadingTitle
  if (!props.recommendation) return TEXT.emptyTitle
  return labels[props.recommendation.decision] || props.recommendation.decision
})
const bodyText = computed(() => {
  if (props.loading) return TEXT.loadingBody
  return props.recommendation?.recommendation_text || ''
})
const metricStatus = (index) => props.loadingStepItems?.[index]?.status || 'pending'
const metrics = computed(() => [
  {
    label: TEXT.price,
    value: metricNumber(props.recommendation?.price_score ?? props.recommendation?.metrics?.price_score, score.value || '-'),
    status: metricStatus(0),
  },
  {
    label: TEXT.userRating,
    value: userReviewScore.value,
    status: metricStatus(1),
  },
  {
    label: TEXT.taste,
    value: metricNumber(props.recommendation?.taste_score ?? props.recommendation?.metrics?.taste_score, 50),
    status: metricStatus(2),
  },
])
const scoreRingStyle = computed(() => ({
  '--score-percent': `${score.value}%`,
}))
</script>
