<template>
  <img v-if="currentSrc && !failed" :src="currentSrc" :alt="alt" @error="handleError" />
  <div v-else :class="fallbackClass">{{ fallbackText }}</div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  src: { type: String, default: '' },
  alt: { type: String, default: '' },
  steamAppId: { type: [String, Number], default: '' },
  fallbackClass: { type: String, default: 'image-fallback' },
})

const failed = ref(false)
const sourceIndex = ref(0)

const steamImages = computed(() => {
  if (!props.steamAppId) return []
  const base = `https://cdn.akamai.steamstatic.com/steam/apps/${props.steamAppId}`
  return [`${base}/header.jpg`, `${base}/capsule_616x353.jpg`, `${base}/library_600x900.jpg`]
})
const imageSources = computed(() => {
  const sources = [props.src, ...steamImages.value].filter(Boolean)
  return [...new Set(sources)]
})
const currentSrc = computed(() => imageSources.value[sourceIndex.value] || '')
const fallbackText = computed(() => props.alt?.slice(0, 2) || 'CD')

watch(
  () => [props.src, props.steamAppId],
  () => {
    failed.value = false
    sourceIndex.value = 0
  },
)

const handleError = () => {
  if (sourceIndex.value < imageSources.value.length - 1) {
    sourceIndex.value += 1
    return
  }
  failed.value = true
}
</script>
