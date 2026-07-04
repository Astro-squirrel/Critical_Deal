<template>
  <header class="topbar">
    <SearchBar class="top-search" />
    <div class="top-actions">
      <div
        class="profile-menu"
        @mouseenter="isMenuOpen = true"
        @mouseleave="isMenuOpen = false"
        @focusin="isMenuOpen = true"
        @focusout="isMenuOpen = false"
      >
        <button v-if="auth.user" type="button" class="profile-trigger" :aria-expanded="isMenuOpen">
          <span class="profile-trigger-avatar">
            <img :src="auth.user.avatar_url || defaultProfileAvatar" :alt="auth.user.display_name || auth.user.username || '프로필'" />
          </span>
          <span>{{ auth.user.display_name || auth.user.username || auth.user.email }}</span>
          <ChevronUp v-if="isMenuOpen" :size="16" />
          <ChevronDown v-else :size="16" />
        </button>
        <router-link v-else class="ghost-button" to="/login">로그인</router-link>

        <div v-if="isMenuOpen" class="profile-dropdown">
          <template v-if="auth.user">
            <router-link class="profile-menu-row" to="/profile">
              <span class="profile-menu-avatar">
                <img :src="auth.user.avatar_url || defaultProfileAvatar" :alt="auth.user.display_name || auth.user.username || '프로필'" />
              </span>
              <span>내 정보 / 보유 게임</span>
            </router-link>
            <router-link class="profile-menu-row" to="/wishlist">
              <Heart :size="20" />
              <span>위시리스트</span>
            </router-link>

            <div class="profile-menu-divider"></div>

            <div class="profile-menu-row readonly">
              <Globe2 :size="20" />
              <span>국가</span>
              <strong>KR</strong>
            </div>
            <div class="profile-menu-row readonly">
              <Coins :size="20" />
              <span>통화</span>
              <strong>KRW</strong>
            </div>

            <div class="profile-menu-divider"></div>

            <router-link class="profile-menu-row" to="/settings">
              <Settings :size="20" />
              <span>설정</span>
            </router-link>
            <button type="button" class="profile-menu-row logout-row" @mousedown.prevent.stop="logout" @click.prevent.stop>
              <LogOut :size="20" />
              <span>로그아웃</span>
            </button>
          </template>

          <template v-else>
            <router-link class="profile-menu-row" to="/login">
              <LogIn :size="20" />
              <span>로그인 / 회원가입</span>
            </router-link>
          </template>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChevronDown,
  ChevronUp,
  Coins,
  Globe2,
  Heart,
  LogIn,
  LogOut,
  Settings,
} from 'lucide-vue-next'
import SearchBar from './SearchBar.vue'
import defaultProfileAvatar from '../assets/default-profile.svg'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const isMenuOpen = ref(false)

onMounted(() => auth.fetchMe())

const logout = async () => {
  isMenuOpen.value = false
  await auth.logout()
  router.push('/')
}
</script>
