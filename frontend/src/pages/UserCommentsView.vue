<template>
  <AppLayout>
    <div class="user-comments-page">
      <section class="panel list-header user-comments-header">
        <div class="user-comments-profile">
          <img :src="profile.avatar_url || defaultProfileAvatar" :alt="profile.name" />
          <div>
            <span>작성자 댓글</span>
            <h1>{{ profile.name || '사용자' }}</h1>
            <p>{{ pagination.count }}개의 댓글</p>
          </div>
        </div>
      </section>

      <LoadingSpinner v-if="loading" />
      <p v-else-if="!comments.length" class="profile-empty">작성한 댓글이 없습니다.</p>
      <section v-else class="user-comment-list">
        <article v-for="comment in comments" :key="comment.id" class="user-comment-row">
          <router-link class="user-comment-game-image" :to="{ name: 'game-detail', params: { id: comment.game.id } }">
            <GameImage
              :src="comment.game.thumbnail || comment.game.hero_image"
              :alt="comment.game.title"
              :steam-app-id="comment.game.steam_app_id"
            />
          </router-link>
          <div class="user-comment-main">
            <router-link class="user-comment-game-title" :to="{ name: 'game-detail', params: { id: comment.game.id } }">
              {{ comment.game.title }}
            </router-link>
            <div class="user-comment-meta">
              <span v-if="comment.steam_playtime_minutes">Steam 플레이 {{ formatPlaytime(comment.steam_playtime_minutes) }}</span>
              <span>{{ formatCommentDate(comment.created_at) }}</span>
            </div>
            <p>{{ comment.content }}</p>
            <div class="user-comment-reactions">
              <span><ThumbsUp aria-hidden="true" :size="15" /> {{ comment.like_count }}</span>
              <span><ThumbsDown aria-hidden="true" :size="15" /> {{ comment.dislike_count }}</span>
            </div>
          </div>
        </article>

        <div v-if="totalPages > 1" class="pagination-bar user-comment-pagination" aria-label="댓글 페이지 선택">
          <button
            v-if="hasLeadingEllipsis"
            type="button"
            class="pagination-jump"
            aria-label="첫 댓글 페이지"
            @click="changePage(1)"
          >
            ...
          </button>
          <button
            v-for="pageNumber in pageNumbers"
            :key="pageNumber"
            type="button"
            class="pagination-number"
            :class="{ active: pageNumber === page }"
            :aria-current="pageNumber === page ? 'page' : undefined"
            @click="changePage(pageNumber)"
          >
            {{ pageNumber }}
          </button>
          <button
            v-if="hasTrailingEllipsis"
            type="button"
            class="pagination-jump"
            :aria-label="`마지막 댓글 페이지 ${totalPages}`"
            @click="changePage(totalPages)"
          >
            ...
          </button>
        </div>
      </section>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ThumbsDown, ThumbsUp } from 'lucide-vue-next'
import { gamesApi } from '../api/games'
import AppLayout from '../layouts/AppLayout.vue'
import GameImage from '../components/GameImage.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import defaultProfileAvatar from '../assets/default-profile.svg'

const route = useRoute()
const router = useRouter()
const comments = ref([])
const profile = ref({})
const pagination = ref({ count: 0, page: 1, page_size: 10, total_pages: 1 })
const loading = ref(false)
const pageWindowRadius = 2

const page = computed(() => Math.max(1, Number(route.query.page || 1)))
const totalPages = computed(() => Math.max(1, Number(pagination.value.total_pages || 1)))
const pageNumbers = computed(() => {
  const currentPage = Math.min(totalPages.value, Math.max(1, page.value))
  const firstPage = Math.max(1, currentPage - pageWindowRadius)
  const lastPage = Math.min(totalPages.value, currentPage + pageWindowRadius)
  return Array.from({ length: Math.max(0, lastPage - firstPage + 1) }, (_, index) => firstPage + index)
})
const hasLeadingEllipsis = computed(() => pageNumbers.value[0] > 1)
const hasTrailingEllipsis = computed(() => pageNumbers.value.at(-1) < totalPages.value)

const loadComments = async () => {
  loading.value = true
  try {
    const response = await gamesApi.userComments(route.params.id, { page: page.value })
    profile.value = response.user || {}
    comments.value = response.comments || []
    pagination.value = response.pagination || { count: comments.value.length, page: 1, page_size: 10, total_pages: 1 }
  } finally {
    loading.value = false
  }
}

const changePage = (nextPage) => {
  const targetPage = Math.min(totalPages.value, Math.max(1, nextPage))
  router.push({
    name: 'user-comments',
    params: { id: route.params.id },
    query: targetPage > 1 ? { page: targetPage } : {},
  })
}

const formatPlaytime = (minutes) => {
  const total = Number(minutes || 0)
  if (total < 60) return `${total}분`
  const hours = Math.floor(total / 60)
  const mins = total % 60
  return mins ? `${hours}시간 ${mins}분` : `${hours}시간`
}

const formatCommentDate = (value) => {
  if (!value) return ''
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

onMounted(loadComments)
watch(() => [route.params.id, route.query.page], loadComments)
</script>
