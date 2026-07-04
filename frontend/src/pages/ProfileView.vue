<template>
  <AppLayout>
    <section class="panel profile-panel">
      <div class="profile-header">
        <img :src="profile?.user?.avatar_url || defaultProfileAvatar" :alt="displayName" />
        <div class="profile-identity">
          <p class="eyebrow">내 정보</p>
          <h1>{{ displayName }}</h1>
          <p>{{ profile?.user?.email || auth.user?.email || '로그인이 필요합니다.' }}</p>
          <a v-if="profile?.steam?.profile_url" :href="profile.steam.profile_url" target="_blank" rel="noreferrer">Steam 프로필 보기</a>
          <router-link class="profile-wishlist-link" to="/wishlist">위시리스트</router-link>
        </div>
      </div>

      <div v-if="auth.user" class="profile-stats">
        <div>
          <span>보유 게임</span>
          <strong>{{ ownedGames.length }}개</strong>
        </div>
        <div>
          <span>총 플레이타임</span>
          <strong>{{ formatPlaytime(totalPlaytime) }}</strong>
        </div>
      </div>

      <p v-if="message" class="profile-message">{{ message }}</p>
      <p v-if="loading" class="loading">내 정보를 불러오는 중...</p>

      <section v-if="auth.user" class="owned-games-section">
        <div class="section-title">
          <h2>내가 가진 게임</h2>
          <button type="button" @click="loadProfile">새로고침</button>
        </div>

        <div v-if="ownedGames.length" class="owned-game-list">
          <article v-for="game in ownedGames" :key="game.id" class="owned-game-row">
            <img v-if="game.thumbnail" :src="game.thumbnail" :alt="game.title" />
            <div v-else class="image-fallback">{{ game.title?.slice(0, 2) }}</div>
            <div>
              <h3>{{ game.title }}</h3>
              <p>{{ game.source === 'manual' ? '직접 추가' : 'Steam 동기화' }}</p>
            </div>
            <strong>{{ formatPlaytime(game.playtime_minutes) }}</strong>
            <button v-if="game.source === 'manual'" type="button" class="secondary-button" @click="removeOwnedGame(game.id)">삭제</button>
          </article>
        </div>
        <p v-else-if="!loading" class="profile-empty">아직 보유 게임이 없습니다.</p>
      </section>
    </section>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { accountsApi } from '../api/accounts'
import defaultProfileAvatar from '../assets/default-profile.svg'
import AppLayout from '../layouts/AppLayout.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const message = ref('')
const profile = ref(null)
const loading = ref(false)

const ownedGames = computed(() => profile.value?.owned_games || [])
const displayName = computed(() => profile.value?.user?.display_name || auth.user?.display_name || auth.user?.username || '사용자')
const totalPlaytime = computed(() => ownedGames.value.reduce((sum, game) => sum + Number(game.playtime_minutes || 0), 0))

const formatPlaytime = (minutes) => {
  const total = Number(minutes || 0)
  if (total < 60) return `${total}분`
  const hours = Math.floor(total / 60)
  const mins = total % 60
  return mins ? `${hours}시간 ${mins}분` : `${hours}시간`
}

const loadProfile = async () => {
  if (!auth.user) return
  loading.value = true
  message.value = ''
  try {
    profile.value = await accountsApi.profile()
    auth.user = profile.value.user
  } catch (error) {
    message.value = error.message
  } finally {
    loading.value = false
  }
}

const removeOwnedGame = async (id) => {
  await accountsApi.removeOwnedGame(id)
  await loadProfile()
}

onMounted(async () => {
  if (!auth.user) await auth.fetchMe()
  await loadProfile()
})
</script>
