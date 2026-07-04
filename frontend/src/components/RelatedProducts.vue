<template>
  <section v-if="hasProducts" class="panel related-products-panel">
    <div class="section-title related-products-title">
      <h2>{{ labels.title }}</h2>
    </div>

    <div v-if="visibleProducts.length" class="related-products-list">
      <component
        v-for="product in visibleProducts"
        :is="product.game_id ? RouterLink : 'a'"
        :key="`dlc-${product.id}`"
        class="related-product-row"
        :to="product.game_id ? `/games/${product.game_id}` : undefined"
        :href="product.game_id ? undefined : product.url"
        :target="product.game_id ? undefined : '_blank'"
        :rel="product.game_id ? undefined : 'noreferrer'"
      >
        <img v-if="product.thumbnail" :src="product.thumbnail" :alt="product.title" />
        <div v-else class="related-product-fallback">{{ product.title?.slice(0, 2) }}</div>
        <div class="related-product-copy">
          <strong>{{ product.title }}</strong>
          <span v-if="product.included_count">{{ labels.included }} {{ product.included_count }}{{ labels.countSuffix }}</span>
          <span v-else>{{ labels.dlc }}</span>
        </div>
        <div class="related-product-price" :class="{ discounted: isDiscounted(product) }">
          <span v-if="isDiscounted(product)" class="discount">-{{ percent(product.discount_rate) }}</span>
          <div>
            <del v-if="isDiscounted(product)">{{ money(product.original_price) }}</del>
            <strong>{{ product.is_free ? labels.free : money(product.current_price) }}</strong>
          </div>
        </div>
      </component>
    </div>

    <p v-else class="related-products-empty">{{ labels.noDlc }}</p>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { money, percent } from '../utils/format'

const labels = {
  title: '\uad00\ub828 \uc0c1\ud488',
  included: '\ud3ec\ud568 \uc0c1\ud488',
  countSuffix: '\uac1c',
  dlc: '\ub2e4\uc6b4\ub85c\ub4dc \ucf58\ud150\uce20',
  free: '\ubb34\ub8cc',
  noDlc: '\ud45c\uc2dc\ud560 DLC\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.',
}

const props = defineProps({
  products: { type: Object, default: () => ({ dlc: [], bundles: [] }) },
})

const dlc = computed(() => props.products?.dlc || [])
const hasProducts = computed(() => dlc.value.length)
const visibleProducts = computed(() => dlc.value)

const isDiscounted = (product) =>
  Number(product.discount_rate || 0) > 0 && Number(product.original_price || 0) > Number(product.current_price || 0)
</script>
