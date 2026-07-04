<template>
  <section class="panel side-panel">
    <div class="section-title">
      <div>
        <span class="section-eyebrow">Free now</span>
        <h2>지금 무료로 받기</h2>
      </div>
      <router-link to="/free-games">전체 보기</router-link>
    </div>
    <div class="free-list">
      <article v-for="game in games" :key="game.id || game.title" class="free-row">
        <img v-if="game.thumbnail" :src="game.thumbnail" :alt="game.title" />
        <div v-else class="free-image-fallback">{{ game.title?.slice(0, 2) }}</div>
        <div>
          <strong>{{ game.title }}</strong>
          <p>{{ game.source || 'Epic Games' }}</p>
        </div>
        <a :href="game.claim_url" target="_blank" rel="noreferrer">받으러 가기</a>
      </article>
      <p v-if="!games.length" class="empty-preview">현재 무료 배포 정보를 불러오지 못했습니다.</p>
    </div>
  </section>
</template>

<script setup>
defineProps({ games: { type: Array, default: () => [] } })
</script>
