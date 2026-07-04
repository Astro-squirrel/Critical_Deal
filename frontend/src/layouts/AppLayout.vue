<template>
  <div class="app-shell">
    <header class="app-header">
      <router-link class="app-title" to="/">Critical Deal</router-link>
      <nav class="top-tabs" aria-label="Primary navigation">
        <router-link
          v-for="tab in tabs"
          :key="tab.label"
          :to="tab.to"
          class="top-tab"
          :class="{ active: isTabActive(tab) }"
        >
          {{ tab.label }}
        </router-link>
      </nav>
      <Navbar />
    </header>

    <main class="main-panel">
      <slot />
    </main>
    <AiChatWidget />
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import AiChatWidget from '../components/AiChatWidget.vue'
import Navbar from '../components/Navbar.vue'

const route = useRoute()

const tabs = [
  { label: '홈', to: '/', name: 'home' },
  { label: '검색', to: '/games', name: 'search' },
  { label: '인기 할인', to: { path: '/games', query: { ordering: '-steam_review_count', discounted: '1' } }, name: 'popular' },
]

const isTabActive = (tab) => {
  if (tab.name === 'home') return route.path === '/'
  if (tab.name === 'popular') return isPopularTabRoute()
  if (tab.name === 'search') return route.path === '/games' && !isPopularTabRoute()
  return false
}

const isPopularTabRoute = () =>
  route.path === '/games' && route.query.ordering === '-steam_review_count' && route.query.discounted === '1'
</script>
