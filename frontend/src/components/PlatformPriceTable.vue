<template>
  <section class="panel">
    <div class="section-title"><h2>Steam 가격</h2></div>
    <table class="price-table">
      <thead>
        <tr>
          <th>현재가</th>
          <th>할인율</th>
          <th>역대 최저가</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="price in steamPrices" :key="price.id">
          <td>{{ money(price.current_price) }}</td>
          <td>-{{ price.discount_rate }}%</td>
          <td>{{ money(price.historical_low_price) }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { money } from '../utils/format'

const props = defineProps({ prices: { type: Array, default: () => [] } })

const steamPrices = computed(() => props.prices.filter((price) => price.store?.name?.toLowerCase() === 'steam'))
</script>
