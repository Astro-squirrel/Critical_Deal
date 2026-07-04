<template>
  <AppLayout>
    <LoadingSpinner v-if="loading" variant="detail" />
    <div v-else-if="game" class="detail-stack">
      <section class="detail-hero panel">
        <div class="detail-media">
          <GameImage
            :src="detailImage"
            :alt="game.title"
            :steam-app-id="game.steam_app_id"
            fallback-class="detail-image-fallback"
          />
        </div>
        <div class="detail-info">
          <div class="detail-title-row">
            <h1>{{ game.title }}</h1>
            <button
              class="wishlist-heart"
              type="button"
              :class="{ active: wishlisted }"
              :disabled="wishLoading"
              :aria-pressed="wishlisted"
              :aria-label="wishlisted ? '위시리스트에서 제거' : '위시리스트에 추가'"
              :data-tooltip="wishlistTooltip"
              @click="toggleWish"
            >
              <Heart aria-hidden="true" :size="28" :stroke-width="2.2" :fill="wishlisted ? 'currentColor' : 'none'" />
            </button>
          </div>
          <p class="detail-description">{{ genreText }}</p>
          <p class="detail-review-line">{{ reviewText }}</p>
          <div class="tag-row detail-tags">
            <span v-for="tag in visibleTags" :key="tag">{{ tag }}</span>
          </div>
          <div class="detail-commerce-row">
            <div v-if="steamPrice" class="detail-price-summary">
              <div>
                <span>{{ detailLabels.steamCurrentPrice }}</span>
                <div class="detail-current-price" :class="{ discounted: isDiscounted(steamPrice) }">
                  <strong>{{ money(steamPrice.current_price) }}</strong>
                  <span v-if="isDiscounted(steamPrice)" class="discount">-{{ percent(steamPrice.discount_rate) }}</span>
                </div>
                <del v-if="isDiscounted(steamPrice)">{{ money(steamPrice.original_price) }}</del>
              </div>
            </div>
            <a
              v-if="steamStoreUrl"
              class="steam-store-action detail-steam-action"
              :href="steamStoreUrl"
              target="_blank"
              rel="noreferrer"
            >
              {{ detailLabels.steamStore }}
            </a>
          </div>
        </div>
      </section>
      <p v-if="secondaryLoading" class="detail-loading-note">{{ detailLabels.secondaryLoading }}</p>
      <div class="detail-content-grid">
        <div class="detail-main-column">
          <RecommendationScore
            v-if="aiLoading"
            loading
            :loading-step-items="aiLoadingScoreItems"
            :review-score="steamReviewScore"
          />
          <section v-else-if="!aiAnalysis" class="panel ai-analysis-prompt">
            <div>
              <span class="eyebrow">{{ aiPromptLabels.eyebrow }}</span>
              <h2>{{ aiPromptLabels.title }}</h2>
              <p>{{ aiPromptLabels.description }}</p>
            </div>
            <button class="ai-analysis-button" type="button" @click="loadAIAnalysis">
              <span>{{ aiPromptLabels.button }}</span>
            </button>
            <p v-if="aiError" class="analysis-error">{{ aiError }}</p>
          </section>
          <RecommendationScore v-else :recommendation="aiAnalysis" :review-score="steamReviewScore" />
          <section class="panel detail-chart-panel">
            <div class="section-title">
              <h2>가격 추이</h2>
              <span>{{ discountSummaryText }}</span>
            </div>
            <PriceChart :history="history" />
            <div class="recent-discount-table">
              <div class="recent-discount-head">
                <h3>최근 할인 이벤트</h3>
                <span>최대 5개</span>
              </div>
              <div v-if="recentDiscountEvents.length" class="discount-table-wrap">
                <table class="discount-event-table">
                  <thead>
                    <tr>
                      <th>기간</th>
                      <th>할인율</th>
                      <th>할인가</th>
                      <th>정가</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="event in recentDiscountEvents" :key="`${event.start}-${event.end}-${event.price}`">
                      <td>{{ discountEventPeriod(event) }}</td>
                      <td><span class="discount">-{{ percent(event.discount) }}</span></td>
                      <td>{{ money(event.price) }}</td>
                      <td>{{ money(event.original) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p v-else class="detail-stat-empty">저장된 할인 이벤트가 아직 없습니다.</p>
            </div>
          </section>

          <section class="panel detail-comments-panel">
            <div class="section-title">
              <h2>댓글</h2>
              <span>{{ commentTotalCount }}개</span>
            </div>

            <form v-if="auth.user" class="comment-form" @submit.prevent="submitComment">
              <textarea
                v-model="commentDraft"
                maxlength="1200"
                rows="3"
                placeholder="이 게임에 대한 생각을 남겨보세요."
              ></textarea>
              <div class="comment-form-foot">
                <span>{{ commentDraft.length }}/1200</span>
                <button type="submit" :disabled="!canSubmitComment || commentSubmitting">
                  {{ commentSubmitting ? '등록 중' : '댓글 등록' }}
                </button>
              </div>
            </form>
            <p v-else class="comment-login-note">
              댓글을 남기려면 <router-link :to="{ path: '/login', query: { next: route.fullPath } }">로그인</router-link>이 필요합니다.
            </p>
            <p v-if="commentMessage" class="comment-message">{{ commentMessage }}</p>

            <div v-if="commentLoading" class="detail-stat-empty">댓글을 불러오는 중입니다.</div>
            <div v-else-if="commentDisplayItems.length" class="comment-list">
              <template v-for="item in commentDisplayItems" :key="item.id">
              <div v-if="item.type === 'divider'" class="comment-section-divider"></div>
              <article v-else class="comment-row">
                <router-link class="comment-avatar-link" :to="{ name: 'user-comments', params: { id: item.comment.author_id } }">
                  <img :src="item.comment.author_avatar_url || defaultProfileAvatar" :alt="item.comment.author_name" />
                </router-link>
                <div class="comment-body">
                  <div class="comment-head">
                    <div class="comment-main">
                      <div class="comment-meta-line">
                        <router-link class="comment-author-link" :to="{ name: 'user-comments', params: { id: item.comment.author_id } }">
                          {{ item.comment.author_name }}
                        </router-link>
                        <span>{{ formatCommentRelativeDate(item.comment.created_at) }}</span>
                        <span v-if="isEditedComment(item.comment)">수정됨</span>
                        <span v-if="item.comment.steam_playtime_minutes">Steam 플레이 {{ formatPlaytime(item.comment.steam_playtime_minutes) }}</span>
                      </div>
                      <template v-if="editingCommentId === item.comment.id">
                        <textarea
                          v-model="editingCommentContent"
                          class="comment-edit-input"
                          maxlength="1200"
                          rows="3"
                        ></textarea>
                        <div class="comment-edit-actions">
                          <button type="button" :disabled="!canSaveEditedComment || commentSavingId === item.comment.id" @click="saveEditedComment(item.comment)">
                            {{ commentSavingId === item.comment.id ? '저장 중' : '저장' }}
                          </button>
                          <button type="button" @click="cancelEditComment">취소</button>
                        </div>
                      </template>
                      <p v-else class="comment-content">{{ item.comment.content }}</p>
                    </div>
                    <div v-if="item.comment.can_edit && editingCommentId !== item.comment.id" class="comment-menu-wrap">
                      <button type="button" class="comment-menu-trigger" :aria-expanded="openCommentMenuId === item.comment.id" @click.stop="toggleCommentMenu(item.comment)">
                        <MoreVertical aria-hidden="true" :size="19" />
                      </button>
                      <div v-if="openCommentMenuId === item.comment.id" class="comment-owner-menu">
                        <button type="button" @click="startEditComment(item.comment)">수정</button>
                        <button
                          type="button"
                          class="danger"
                          :disabled="commentDeletingId === item.comment.id"
                          @click="deleteOwnComment(item.comment)"
                        >
                          {{ commentDeletingId === item.comment.id ? '삭제 중' : '삭제' }}
                        </button>
                      </div>
                    </div>
                  </div>
                  <div v-if="editingCommentId !== item.comment.id" class="comment-actions-row">
                    <div class="comment-reactions">
                      <button
                        type="button"
                        class="comment-reaction-button like"
                        :class="{ active: item.comment.my_reaction === 'like' }"
                        :disabled="reactionLoadingId === item.comment.id"
                        @click="reactToComment(item.comment, 'like')"
                      >
                        <ThumbsUp aria-hidden="true" :size="16" />
                        <span>{{ item.comment.like_count }}</span>
                      </button>
                      <button
                        type="button"
                        class="comment-reaction-button dislike"
                        :class="{ active: item.comment.my_reaction === 'dislike' }"
                        :disabled="reactionLoadingId === item.comment.id"
                        @click="reactToComment(item.comment, 'dislike')"
                      >
                        <ThumbsDown aria-hidden="true" :size="16" />
                        <span>{{ item.comment.dislike_count }}</span>
                      </button>
                    </div>
                    <button type="button" class="comment-reply-button" @click="toggleReplySection(item.comment)">
                      <span>{{ isReplySectionOpen(item.comment) ? '답글 숨기기' : `답글 ${item.comment.replies?.length || 0}개` }}</span>
                      <ChevronUp v-if="isReplySectionOpen(item.comment)" aria-hidden="true" :size="15" />
                      <ChevronDown v-else aria-hidden="true" :size="15" />
                    </button>
                  </div>

                  <div v-if="isReplySectionOpen(item.comment)" class="comment-reply-section">
                    <form
                      v-if="auth.user"
                      class="comment-reply-form"
                      @submit.prevent="submitReply(item.comment)"
                    >
                      <textarea
                        v-model="replyDrafts[item.comment.id]"
                        maxlength="1200"
                        rows="2"
                        placeholder="답글을 남겨보세요."
                      ></textarea>
                      <div class="comment-reply-form-foot">
                        <span>{{ (replyDrafts[item.comment.id] || '').length }}/1200</span>
                        <button type="button" @click="cancelReplyForm(item.comment)">취소</button>
                        <button
                          type="submit"
                          :disabled="!(replyDrafts[item.comment.id] || '').trim() || replySubmittingId === item.comment.id"
                        >
                          {{ replySubmittingId === item.comment.id ? '등록 중' : '답글 등록' }}
                        </button>
                      </div>
                    </form>
                    <p v-else class="comment-reply-login-note">
                      답글을 남기려면 <router-link :to="{ path: '/login', query: { next: route.fullPath } }">로그인</router-link>이 필요합니다.
                    </p>

                    <div v-if="item.comment.replies?.length" class="comment-reply-list">
                      <article v-for="reply in item.comment.replies" :key="reply.id" class="comment-reply-row">
                        <router-link class="comment-avatar-link reply-avatar-link" :to="{ name: 'user-comments', params: { id: reply.author_id } }">
                          <img :src="reply.author_avatar_url || defaultProfileAvatar" :alt="reply.author_name" />
                        </router-link>
                        <div class="comment-reply-body">
                          <div class="comment-head">
                            <div class="comment-main">
                              <div class="comment-meta-line">
                                <router-link class="comment-author-link" :to="{ name: 'user-comments', params: { id: reply.author_id } }">
                                  {{ reply.author_name }}
                                </router-link>
                                <span>{{ formatCommentRelativeDate(reply.created_at) }}</span>
                                <span v-if="isEditedComment(reply)">수정됨</span>
                                <span v-if="reply.steam_playtime_minutes">Steam 플레이 {{ formatPlaytime(reply.steam_playtime_minutes) }}</span>
                              </div>
                              <template v-if="editingCommentId === reply.id">
                                <textarea
                                  v-model="editingCommentContent"
                                  class="comment-edit-input"
                                  maxlength="1200"
                                  rows="2"
                                ></textarea>
                                <div class="comment-edit-actions">
                                  <button type="button" :disabled="!canSaveEditedComment || commentSavingId === reply.id" @click="saveEditedComment(reply)">
                                    {{ commentSavingId === reply.id ? '저장 중' : '저장' }}
                                  </button>
                                  <button type="button" @click="cancelEditComment">취소</button>
                                </div>
                              </template>
                              <p v-else class="comment-content">{{ reply.content }}</p>
                            </div>
                            <div v-if="reply.can_edit && editingCommentId !== reply.id" class="comment-menu-wrap">
                              <button type="button" class="comment-menu-trigger" :aria-expanded="openCommentMenuId === reply.id" @click.stop="toggleCommentMenu(reply)">
                                <MoreVertical aria-hidden="true" :size="18" />
                              </button>
                              <div v-if="openCommentMenuId === reply.id" class="comment-owner-menu">
                                <button type="button" @click="startEditComment(reply)">수정</button>
                                <button
                                  type="button"
                                  class="danger"
                                  :disabled="commentDeletingId === reply.id"
                                  @click="deleteOwnComment(reply)"
                                >
                                  {{ commentDeletingId === reply.id ? '삭제 중' : '삭제' }}
                                </button>
                              </div>
                            </div>
                          </div>
                          <div v-if="editingCommentId !== reply.id" class="comment-actions-row">
                            <div class="comment-reactions">
                              <button
                                type="button"
                                class="comment-reaction-button like"
                                :class="{ active: reply.my_reaction === 'like' }"
                                :disabled="reactionLoadingId === reply.id"
                                @click="reactToComment(reply, 'like')"
                              >
                                <ThumbsUp aria-hidden="true" :size="15" />
                                <span>{{ reply.like_count }}</span>
                              </button>
                              <button
                                type="button"
                                class="comment-reaction-button dislike"
                                :class="{ active: reply.my_reaction === 'dislike' }"
                                :disabled="reactionLoadingId === reply.id"
                                @click="reactToComment(reply, 'dislike')"
                              >
                                <ThumbsDown aria-hidden="true" :size="15" />
                                <span>{{ reply.dislike_count }}</span>
                              </button>
                            </div>
                          </div>
                        </div>
                      </article>
                    </div>
                  </div>
                </div>
              </article>
              </template>
              <div v-if="commentTotalPages > 1" class="pagination-bar comment-pagination" aria-label="댓글 페이지 선택">
                <button
                  v-if="commentHasLeadingEllipsis"
                  type="button"
                  class="pagination-jump"
                  aria-label="첫 댓글 페이지"
                  @click="changeCommentPage(1)"
                >
                  ...
                </button>
                <button
                  v-for="pageNumber in commentPageNumbers"
                  :key="pageNumber"
                  type="button"
                  class="pagination-number"
                  :class="{ active: pageNumber === commentPage }"
                  :aria-current="pageNumber === commentPage ? 'page' : undefined"
                  @click="changeCommentPage(pageNumber)"
                >
                  {{ pageNumber }}
                </button>
                <button
                  v-if="commentHasTrailingEllipsis"
                  type="button"
                  class="pagination-jump"
                  :aria-label="`마지막 댓글 페이지 ${commentTotalPages}`"
                  @click="changeCommentPage(commentTotalPages)"
                >
                  ...
                </button>
              </div>
            </div>
            <p v-else class="detail-stat-empty">아직 댓글이 없습니다.</p>
          </section>
        </div>

        <div class="detail-side-column">
          <section class="panel detail-community-panel">
            <div class="detail-stat-block">
              <div class="detail-stat-heading">
                <Users aria-hidden="true" :size="25" />
                <h2>Players</h2>
              </div>
              <div class="player-stat-values">
                <span>Current <strong>{{ formatStatNumber(playerStats.current) }}</strong></span>
                <span>Peak <strong>{{ formatStatNumber(playerStats.peak) }}</strong></span>
              </div>
              <div class="player-chart" :class="{ empty: !playerChartPoints }">
                <svg v-if="playerChartPoints" viewBox="0 0 100 44" preserveAspectRatio="none" aria-hidden="true">
                  <polygon :points="playerChartFillPoints" />
                  <polyline :points="playerChartPoints" />
                </svg>
                <span v-else>플레이어 데이터 없음</span>
              </div>
              <div class="player-chart-foot">
                <span>Last two weeks</span>
                <span>Daily avg</span>
              </div>
            </div>

            <div class="detail-stat-block">
              <div class="detail-stat-heading">
                <ThumbsUp aria-hidden="true" :size="24" />
                <h2>Reviews</h2>
              </div>
              <div v-if="reviewSources.length" class="review-source-list">
                <div v-for="source in reviewSources" :key="source.name" class="review-source-row">
                  <div class="review-score-line">
                    <span class="review-positive">
                      <ThumbsUp aria-hidden="true" :size="13" />
                      {{ source.positive }}%
                    </span>
                    <span class="review-negative">
                      {{ source.negative }}%
                      <ThumbsDown aria-hidden="true" :size="13" />
                    </span>
                  </div>
                  <div class="review-meter" aria-hidden="true">
                    <span class="positive" :style="{ width: `${source.positive}%` }"></span>
                    <span class="negative" :style="{ width: `${source.negative}%` }"></span>
                  </div>
                  <div class="review-source-foot">
                    <strong>{{ source.name }}</strong>
                    <span>{{ source.countLabel }}</span>
                  </div>
                </div>
              </div>
              <p v-else class="detail-stat-empty">리뷰 데이터 없음</p>
            </div>
          </section>
          <section class="panel other-price-panel">
            <div class="section-title">
              <h2>{{ detailLabels.otherStoreLowest }}</h2>
            </div>
            <div v-if="otherPrices.length" class="other-price-list">
              <a
                v-for="price in otherPrices"
                :key="price.store_name"
                class="other-price-row"
                :href="price.url"
                target="_blank"
                rel="noreferrer"
              >
                <div>
                  <strong>{{ price.store_name }}</strong>
                  <span v-if="storeSavings(price) > 0">Steam보다 {{ money(storeSavings(price)) }} 저렴</span>
                  <span v-else>보조 가격 정보</span>
                </div>
                <div class="other-price-value" :class="{ discounted: isDiscounted(price) }">
                  <span v-if="isDiscounted(price)" class="discount">-{{ percent(price.discount_rate) }}</span>
                  <strong>{{ money(price.current_price) }}</strong>
                </div>
              </a>
            </div>
            <p v-else class="detail-stat-empty">다른 스토어 가격 정보 없음</p>
          </section>
          <RelatedProducts :products="relatedProducts" />
        </div>
      </div>
    </div>
    <section v-else class="panel list-header">
      <h1>상세 정보를 불러오지 못했습니다</h1>
      <p>{{ error }}</p>
    </section>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ChevronDown, ChevronUp, Heart, MoreVertical, ThumbsDown, ThumbsUp, Users } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { gamesApi } from '../api/games'
import { wishlistApi } from '../api/wishlist'
import AppLayout from '../layouts/AppLayout.vue'
import { useAuthStore } from '../stores/auth'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import PriceChart from '../components/PriceChart.vue'
import RecommendationScore from '../components/RecommendationScore.vue'
import RelatedProducts from '../components/RelatedProducts.vue'
import GameImage from '../components/GameImage.vue'
import defaultProfileAvatar from '../assets/default-profile.svg'
import { money, percent } from '../utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const game = ref(null)
const history = ref([])
const aiAnalysis = ref(null)
const otherPrices = ref([])
const relatedProducts = ref({ dlc: [], bundles: [] })
const topComments = ref([])
const comments = ref([])
const commentPage = ref(1)
const commentPagination = ref({ count: 0, page: 1, page_size: 10, total_pages: 1 })
const commentTotalCount = ref(0)
const commentDraft = ref('')
const replyDrafts = ref({})
const expandedReplyIds = ref([])
const editingCommentId = ref(null)
const editingCommentContent = ref('')
const openCommentMenuId = ref(null)
const loading = ref(true)
const secondaryLoading = ref(false)
const aiLoading = ref(false)
const aiLoadingStage = ref(0)
const commentLoading = ref(false)
const commentSubmitting = ref(false)
const replySubmittingId = ref(null)
const reactionLoadingId = ref(null)
const commentSavingId = ref(null)
const commentDeletingId = ref(null)
const error = ref('')
const aiError = ref('')
const commentMessage = ref('')
const wishlisted = ref(false)
const wishlistItemId = ref(null)
const wishLoading = ref(false)
const wishMessage = ref('')
const aiPromptLabels = {
  eyebrow: '\u0041\u0049 \uad6c\ub9e4 \ubd84\uc11d',
  title: '\uad6c\ub9e4 \ud0c0\uc774\ubc0d \ubd84\uc11d',
  description: '\u0041\u0049\uac00 \uac00\uaca9 \uae30\ub85d\uacfc \ud560\uc778\uc728\uc744 \ubc14\ud0d5\uc73c\ub85c \uad6c\ub9e4 \ud0c0\uc774\ubc0d\uc744 \ubd84\uc11d\ud569\ub2c8\ub2e4.',
  loadingDescription:
    '\uac00\uaca9, \ucde8\ud5a5, \ud3c9\uac00 \uc2e0\ud638\ub97c \uc815\ub9ac\ud558\uace0 \u0041\u0049 \ubd84\uc11d \ubb38\uc7a5\uc744 \ub9cc\ub4dc\ub294 \uc911\uc785\ub2c8\ub2e4.',
  button: '\u0041\u0049 \uad6c\ub9e4 \ubd84\uc11d\ud558\uae30',
  loadingButton: '\ubd84\uc11d \uc9c4\ud589 \uc911',
}
const aiLoadingSteps = [
  '\uac00\uaca9 \uae30\ub85d \ud655\uc778',
  '\uc720\uc800 \ud3c9\uac00 \ud655\uc778',
  '\ucde8\ud5a5 \uc810\uc218 \uacc4\uc0b0',
]
const detailLabels = {
  steamCurrentPrice: '\u0053\u0074\u0065\u0061\u006d \ud604\uc7ac\uac00',
  steamStore: '\u0053\u0074\u0065\u0061\u006d\uc5d0\uc11c \ubcf4\uae30',
  secondaryLoading: '\uac00\uaca9 \ucd94\uc774\uc640 \ucd94\uac00 \uac00\uaca9 \uc815\ubcf4\ub97c \ubd88\ub7ec\uc624\ub294 \uc911\uc785\ub2c8\ub2e4.',
  otherStoreLowest: '\ub2e4\ub978 \uc2a4\ud1a0\uc5b4 \ucd5c\uc800\uac00',
  partialDataError: '\uc77c\ubd80 \ubd84\uc11d \ub370\uc774\ud130\ub97c \ubd88\ub7ec\uc624\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.',
  aiAnalysisError: '\u0041\u0049 \uad6c\ub9e4 \ubd84\uc11d\uc744 \ubd88\ub7ec\uc624\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.',
  wishAdded: '\uc704\uc2dc\ub9ac\uc2a4\ud2b8\uc5d0 \ucd94\uac00\ud588\uc2b5\ub2c8\ub2e4.',
  loginRequired: '\ub85c\uadf8\uc778 \ud6c4 \uc704\uc2dc\ub9ac\uc2a4\ud2b8\uc5d0 \ucd94\uac00\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.',
  wishAddError: '\uc704\uc2dc\ub9ac\uc2a4\ud2b8\uc5d0 \ucd94\uac00\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.',
  wishRemoved: '\uc704\uc2dc\ub9ac\uc2a4\ud2b8\uc5d0\uc11c \uc81c\uac70\ud588\uc2b5\ub2c8\ub2e4.',
  wishRemoveError: '\uc704\uc2dc\ub9ac\uc2a4\ud2b8\uc5d0\uc11c \uc81c\uac70\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.',
}
const detailImage = computed(() => game.value?.thumbnail || game.value?.hero_image || '')
const steamPrice = computed(() => game.value?.prices?.find((price) => price.store?.name?.toLowerCase() === 'steam') || game.value?.prices?.[0])
const steamStoreUrl = computed(() => {
  if (game.value?.steam_app_id) return `https://store.steampowered.com/app/${game.value.steam_app_id}/`
  const priceUrl = steamPrice.value?.url || ''
  if (priceUrl.includes('store.steampowered.com')) return priceUrl
  if (game.value?.title) return `https://store.steampowered.com/search/?term=${encodeURIComponent(game.value.title)}`
  return ''
})
const tagList = computed(() => {
  const tags = (game.value?.tags || [])
    .map((tag) => (typeof tag === 'string' ? tag : tag?.name))
    .filter(Boolean)
  const genres = (game.value?.genres || []).map((genre) => genre.name).filter(Boolean)
  return [...new Set([...tags, ...genres])].slice(0, 8)
})
const reviewText = computed(() => {
  const score = Number(game.value?.steam_review_score || 0)
  if (!score) return '평가 정보 없음'
  if (score >= 95) return '압도적으로 긍정적'
  if (score >= 80) return '매우 긍정적'
  if (score >= 70) return '대체로 긍정적'
  if (score >= 40) return '복합적'
  return `평가 ${score}%`
})
const steamReviewScore = computed(() => Number(game.value?.steam_review_score || 0))
const canSubmitComment = computed(() => commentDraft.value.trim().length > 0)
const canSaveEditedComment = computed(() => editingCommentContent.value.trim().length > 0)
const commentPageWindowRadius = 2
const commentTotalPages = computed(() => Math.max(1, Number(commentPagination.value.total_pages || 1)))
const commentPageNumbers = computed(() => {
  const currentPage = Math.min(commentTotalPages.value, Math.max(1, commentPage.value))
  const firstPage = Math.max(1, currentPage - commentPageWindowRadius)
  const lastPage = Math.min(commentTotalPages.value, currentPage + commentPageWindowRadius)
  return Array.from({ length: Math.max(0, lastPage - firstPage + 1) }, (_, index) => firstPage + index)
})
const commentHasLeadingEllipsis = computed(() => commentPageNumbers.value[0] > 1)
const commentHasTrailingEllipsis = computed(() => commentPageNumbers.value.at(-1) < commentTotalPages.value)
const commentDisplayItems = computed(() => {
  const items = topComments.value.map((comment) => ({ id: `top-${comment.id}`, type: 'comment', comment }))
  if (topComments.value.length && comments.value.length) {
    items.push({ id: 'comment-divider', type: 'divider' })
  }
  comments.value.forEach((comment) => items.push({ id: `latest-${comment.id}`, type: 'comment', comment }))
  return items
})
const aiLoadingStepItems = computed(() =>
  aiLoadingSteps.map((label, index) => ({
    label,
    index: index + 1,
    status: index < aiLoadingStage.value ? 'done' : index === aiLoadingStage.value ? 'active' : 'pending',
  })),
)
const aiLoadingScoreItems = computed(() =>
  ['가격', '유저 평가', '취향'].map((label, index) => ({
    label,
    status: aiLoadingStage.value > index ? 'done' : aiLoadingStage.value === index ? 'active' : 'pending',
  })),
)
const genreText = computed(() => game.value?.genres?.map((genre) => genre.name).filter(Boolean).join(', ') || '\uc7a5\ub974 \uc815\ubcf4 \uc5c6\uc74c')
const visibleTags = computed(() => {
  if (tagList.value.length) return tagList.value
  return genreText.value.split(', ').filter(Boolean)
})
const numberValue = (...values) => {
  for (const value of values) {
    if (value === null || value === undefined || value === '') continue
    const number = Number(value)
    if (Number.isFinite(number) && number >= 0) return number
  }
  return null
}
const formatHistoryDate = (value) => {
  if (!value) return ''
  return new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value))
}
const daysBetween = (from, to) => {
  const start = Date.parse(from)
  const end = Date.parse(to)
  if (!Number.isFinite(start) || !Number.isFinite(end)) return 0
  return Math.round((end - start) / 86400000)
}
const todayEndTime = () => {
  const today = new Date()
  today.setHours(23, 59, 59, 999)
  return today.getTime()
}
const DISCOUNT_EVENT_GAP_DAYS = 3
const SAME_DISCOUNT_STATE_GAP_DAYS = 14
const sameDiscountState = (event, discount, price, original) =>
  event &&
  Math.round(Number(event.discount || 0)) === Math.round(Number(discount || 0)) &&
  Math.round(Number(event.price || 0)) === Math.round(Number(price || 0)) &&
  Math.round(Number(event.original || 0)) === Math.round(Number(original || 0))
const historyPoints = computed(() =>
  [...history.value]
    .filter((point) => {
      const recordedAt = Date.parse(point?.recorded_at)
      return numberValue(point?.price) > 0 && Number.isFinite(recordedAt) && recordedAt <= todayEndTime()
    })
    .sort((a, b) => Date.parse(a.recorded_at) - Date.parse(b.recorded_at)),
)
const discountEvents = computed(() => {
  const events = []
  let currentEvent = null
  for (const point of historyPoints.value) {
    const discount = numberValue(point.discount_rate) || 0
    if (discount <= 0) {
      if (currentEvent) {
        currentEvent.end = point.recorded_at
        currentEvent.closedByRegularPrice = true
      }
      currentEvent = null
      continue
    }

    const price = numberValue(point.price) || 0
    const original = numberValue(point.original_price, price) || price
    const gapDays = currentEvent ? daysBetween(currentEvent.end, point.recorded_at) : 0
    const shouldExtend =
      currentEvent &&
      (gapDays <= DISCOUNT_EVENT_GAP_DAYS ||
        (gapDays <= SAME_DISCOUNT_STATE_GAP_DAYS && sameDiscountState(currentEvent, discount, price, original)))

    if (shouldExtend) {
      currentEvent.end = point.recorded_at
      currentEvent.discount = Math.max(currentEvent.discount, discount)
      currentEvent.original = Math.max(currentEvent.original, original)
      if (!currentEvent.price || price < currentEvent.price) {
        currentEvent.price = price
      }
      continue
    }

    currentEvent = {
      start: point.recorded_at,
      end: point.recorded_at,
      discount,
      price,
      original,
    }
    events.push(currentEvent)
  }
  if (currentEvent && Number(steamPrice.value?.discount_rate || 0) > 0) {
    currentEvent.ongoing = true
  }
  return events
})
const historyMonthCount = computed(() => {
  if (!historyPoints.value.length) return 0
  const firstDate = Date.parse(historyPoints.value[0].recorded_at)
  const lastDate = Date.parse(historyPoints.value[historyPoints.value.length - 1].recorded_at)
  if (!Number.isFinite(firstDate) || !Number.isFinite(lastDate)) return 0
  const days = Math.max(1, Math.ceil((lastDate - firstDate) / 86400000) + 1)
  return Math.max(1, Math.ceil(days / 30))
})
const discountSummaryText = computed(() => `${historyMonthCount.value}개월동안 ${discountEvents.value.length}번 할인`)
const recentDiscountEvents = computed(() => discountEvents.value.slice(-5).reverse())
const discountEventPeriod = (event) => {
  const start = formatHistoryDate(event.start)
  if (event.ongoing) return `${start} - 진행 중`
  return `${start} - ${formatHistoryDate(event.end || event.start)}`
}
const playerHistoryValues = computed(() => {
  const rawHistory = game.value?.player_history || game.value?.players?.history || game.value?.playerHistory || []
  if (!Array.isArray(rawHistory)) return []
  return rawHistory
    .map((item) => numberValue(item?.players, item?.count, item?.value, item))
    .filter((value) => value !== null)
})
const playerStats = computed(() => {
  const historyValues = playerHistoryValues.value
  const current = numberValue(
    game.value?.current_players,
    game.value?.player_count,
    game.value?.players?.current,
    historyValues.at(-1),
  )
  const peak = numberValue(
    game.value?.peak_players,
    game.value?.players?.peak,
    historyValues.length ? Math.max(...historyValues) : null,
  )
  return { current, peak }
})
const playerChartPoints = computed(() => {
  const values = playerHistoryValues.value
  if (values.length < 2) return ''
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = Math.max(1, max - min)
  return values
    .map((value, index) => {
      const x = values.length === 1 ? 0 : (index / (values.length - 1)) * 100
      const y = 40 - ((value - min) / range) * 34
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
})
const playerChartFillPoints = computed(() => {
  if (!playerChartPoints.value) return ''
  return `0,44 ${playerChartPoints.value} 100,44`
})
const reviewSources = computed(() => {
  const explicitSources = game.value?.review_sources || game.value?.reviews || []
  const sources = Array.isArray(explicitSources)
    ? explicitSources
        .map((source) => normalizeReviewSource(source))
        .filter(Boolean)
    : []
  const hasSteam = sources.some((source) => source.name.toLowerCase() === 'steam')
  const steamSource = normalizeReviewSource({
    name: 'Steam',
    positive: game.value?.steam_review_score,
    count: game.value?.steam_review_count,
  })
  if (steamSource && !hasSteam) sources.unshift(steamSource)
  return sources
})
const normalizeReviewSource = (source) => {
  const positive = Math.max(0, Math.min(100, Math.round(Number(source?.positive ?? source?.score ?? source?.positive_rate ?? 0))))
  const count = Number(source?.count ?? source?.review_count ?? source?.reviews ?? 0)
  if (!positive || !Number.isFinite(count) || count <= 0) return null
  const negative = Math.max(0, 100 - positive)
  return {
    name: source?.name || source?.source || 'Review',
    positive,
    negative,
    count,
    countLabel: `${formatStatNumber(count)} reviews`,
  }
}
const formatStatNumber = (value) => (value === null || value === undefined ? '-' : Number(value).toLocaleString('ko-KR'))
const formatPlaytime = (minutes) => {
  const total = Number(minutes || 0)
  if (total < 60) return `${total}분`
  const hours = Math.floor(total / 60)
  const mins = total % 60
  return mins ? `${hours}시간 ${mins}분` : `${hours}시간`
}
const formatCommentRelativeDate = (value) => {
  if (!value) return ''
  const timestamp = Date.parse(value)
  if (!Number.isFinite(timestamp)) return ''
  const diffSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000))
  if (diffSeconds < 60) return '방금 전'
  const diffMinutes = Math.floor(diffSeconds / 60)
  if (diffMinutes < 60) return `${diffMinutes}분 전`
  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}시간 전`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 30) return `${diffDays}일 전`
  const diffMonths = Math.floor(diffDays / 30)
  if (diffMonths < 12) return `${diffMonths}개월 전`
  return `${Math.floor(diffMonths / 12)}년 전`
}
const isEditedComment = (comment) => {
  const createdAt = Date.parse(comment?.created_at)
  const updatedAt = Date.parse(comment?.updated_at)
  if (!Number.isFinite(createdAt) || !Number.isFinite(updatedAt)) return false
  return updatedAt - createdAt > 5000
}
const wishlistTooltip = computed(() => {
  if (wishLoading.value) return wishlisted.value ? '위시리스트에서 제거 중...' : '위시리스트에 추가 중...'
  return wishlisted.value ? '위시리스트에 추가했습니다.' : '위시리스트 추가'
})

const isDiscounted = (price) => Number(price?.discount_rate || 0) > 0

const storeSavings = (price) => {
  const steam = Number(steamPrice.value?.current_price || 0)
  const other = Number(price?.current_price || 0)
  return steam && other && steam > other ? steam - other : 0
}

const loadWishlistState = async (id) => {
  wishlisted.value = false
  wishlistItemId.value = null
  wishMessage.value = ''
  try {
    const items = await wishlistApi.list()
    const item = items.find((wishlistItem) => wishlistItem.game?.id === Number(id))
    wishlisted.value = Boolean(item)
    wishlistItemId.value = item?.id || null
  } catch {
    // Anonymous users can still view the detail page.
  }
}

const normalizeCommentResponse = (response) => {
  if (Array.isArray(response)) {
    topComments.value = response.slice(0, 3)
    comments.value = response.slice(3, 13)
    commentTotalCount.value = response.length
    commentPagination.value = {
      count: Math.max(0, response.length - 3),
      page: 1,
      page_size: 10,
      total_pages: Math.max(1, Math.ceil(Math.max(0, response.length - 3) / 10)),
    }
    commentPage.value = 1
    return
  }
  topComments.value = response?.top_comments || []
  comments.value = response?.comments || []
  commentTotalCount.value = Number(response?.total_count || topComments.value.length + comments.value.length)
  commentPagination.value = {
    count: Number(response?.pagination?.count || comments.value.length),
    page: Number(response?.pagination?.page || 1),
    page_size: Number(response?.pagination?.page_size || 10),
    total_pages: Number(response?.pagination?.total_pages || 1),
  }
  commentPage.value = commentPagination.value.page
}

const loadComments = async (id, page = commentPage.value) => {
  commentLoading.value = true
  commentMessage.value = ''
  try {
    normalizeCommentResponse(await gamesApi.comments(id, { page }))
  } catch (err) {
    commentMessage.value = err.message || '댓글을 불러오지 못했습니다.'
  } finally {
    commentLoading.value = false
  }
}

const loadGame = async (id) => {
  loading.value = true
  secondaryLoading.value = false
  error.value = ''
  aiError.value = ''
  game.value = null
  history.value = []
  aiAnalysis.value = null
  otherPrices.value = []
  relatedProducts.value = { dlc: [], bundles: [] }
  topComments.value = []
  comments.value = []
  commentPage.value = 1
  commentPagination.value = { count: 0, page: 1, page_size: 10, total_pages: 1 }
  commentTotalCount.value = 0
  commentDraft.value = ''
  replyDrafts.value = {}
  expandedReplyIds.value = []
  replySubmittingId.value = null
  openCommentMenuId.value = null
  cancelEditComment()
  commentMessage.value = ''
  wishlisted.value = false
  wishlistItemId.value = null
  wishMessage.value = ''
  try {
    const detail = await gamesApi.detail(id)
    game.value = detail
    loading.value = false
    secondaryLoading.value = true
    const [historyResult, otherPricesResult, relatedProductsResult, commentsResult, wishlistResult] = await Promise.allSettled([
      gamesApi.history(id),
      gamesApi.otherPrices(id),
      gamesApi.relatedProducts(id),
      loadComments(id, 1),
      loadWishlistState(id),
    ])
    if (historyResult.status === 'fulfilled') history.value = historyResult.value
    if (otherPricesResult.status === 'fulfilled') otherPrices.value = otherPricesResult.value
    if (relatedProductsResult.status === 'fulfilled') relatedProducts.value = relatedProductsResult.value
    if (commentsResult.status === 'rejected') commentMessage.value = commentsResult.reason?.message || '댓글을 불러오지 못했습니다.'
    const failed = [historyResult].find((result) => result.status === 'rejected')
    if (failed) error.value = failed.reason?.message || detailLabels.partialDataError
    if (wishlistResult.status === 'rejected') wishMessage.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
    secondaryLoading.value = false
  }
}

const loadAIAnalysis = async () => {
  if (!game.value || aiLoading.value) return
  aiLoading.value = true
  aiLoadingStage.value = 0
  aiError.value = ''
  const stageTimers = [
    window.setTimeout(() => {
      aiLoadingStage.value = 1
    }, 1200),
    window.setTimeout(() => {
      aiLoadingStage.value = 2
    }, 3200),
  ]
  try {
    const analysis = await gamesApi.aiAnalysis(game.value.id)
    stageTimers.forEach((timer) => window.clearTimeout(timer))
    aiLoadingStage.value = aiLoadingSteps.length
    await new Promise((resolve) => window.setTimeout(resolve, 450))
    aiAnalysis.value = analysis
  } catch (err) {
    aiError.value = err.message || detailLabels.aiAnalysisError
  } finally {
    stageTimers.forEach((timer) => window.clearTimeout(timer))
    aiLoading.value = false
    aiLoadingStage.value = 0
  }
}

const submitComment = async () => {
  const content = commentDraft.value.trim()
  if (!content || !game.value || commentSubmitting.value) return
  commentSubmitting.value = true
  commentMessage.value = ''
  try {
    await gamesApi.addComment(game.value.id, { content })
    commentDraft.value = ''
    await loadComments(game.value.id, 1)
  } catch (err) {
    if (err.status === 401) {
      router.push({ path: '/login', query: { next: route.fullPath } })
      return
    }
    commentMessage.value = err.message || '댓글을 등록하지 못했습니다.'
  } finally {
    commentSubmitting.value = false
  }
}

const isReplySectionOpen = (comment) => expandedReplyIds.value.includes(comment.id)

const toggleReplySection = (comment) => {
  if (isReplySectionOpen(comment)) {
    expandedReplyIds.value = expandedReplyIds.value.filter((id) => id !== comment.id)
    return
  }
  expandedReplyIds.value = [...expandedReplyIds.value, comment.id]
  if (replyDrafts.value[comment.id] === undefined) {
    replyDrafts.value = { ...replyDrafts.value, [comment.id]: '' }
  }
  commentMessage.value = ''
}

const cancelReplyForm = (comment) => {
  if (comment) {
    replyDrafts.value = { ...replyDrafts.value, [comment.id]: '' }
    expandedReplyIds.value = expandedReplyIds.value.filter((id) => id !== comment.id)
  }
}

const submitReply = async (comment) => {
  const content = String(replyDrafts.value[comment.id] || '').trim()
  if (!content || !game.value || replySubmittingId.value) return
  replySubmittingId.value = comment.id
  commentMessage.value = ''
  try {
    await gamesApi.addComment(game.value.id, { content, parent_id: comment.id })
    replyDrafts.value = { ...replyDrafts.value, [comment.id]: '' }
    if (!isReplySectionOpen(comment)) {
      expandedReplyIds.value = [...expandedReplyIds.value, comment.id]
    }
    await loadComments(game.value.id, commentPage.value)
  } catch (err) {
    if (err.status === 401) {
      router.push({ path: '/login', query: { next: route.fullPath } })
      return
    }
    commentMessage.value = err.message || '답글을 등록하지 못했습니다.'
  } finally {
    replySubmittingId.value = null
  }
}

const reactToComment = async (comment, reaction) => {
  if (!game.value || reactionLoadingId.value) return
  if (!auth.user) {
    router.push({ path: '/login', query: { next: route.fullPath } })
    return
  }
  reactionLoadingId.value = comment.id
  commentMessage.value = ''
  try {
    await gamesApi.reactComment(game.value.id, comment.id, reaction)
    await loadComments(game.value.id, commentPage.value)
  } catch (err) {
    commentMessage.value = err.message || '반응을 저장하지 못했습니다.'
  } finally {
    reactionLoadingId.value = null
  }
}

const toggleCommentMenu = (comment) => {
  openCommentMenuId.value = openCommentMenuId.value === comment.id ? null : comment.id
}

const startEditComment = (comment) => {
  openCommentMenuId.value = null
  editingCommentId.value = comment.id
  editingCommentContent.value = comment.content
  commentMessage.value = ''
}

const cancelEditComment = () => {
  editingCommentId.value = null
  editingCommentContent.value = ''
}

const saveEditedComment = async (comment) => {
  const content = editingCommentContent.value.trim()
  if (!game.value || !content || commentSavingId.value) return
  commentSavingId.value = comment.id
  commentMessage.value = ''
  try {
    const updatedComment = await gamesApi.updateComment(game.value.id, comment.id, { content })
    if (updatedComment.parent_id) {
      await loadComments(game.value.id, commentPage.value)
    } else {
      topComments.value = topComments.value.map((item) => (item.id === updatedComment.id ? updatedComment : item))
      comments.value = comments.value.map((item) => (item.id === updatedComment.id ? updatedComment : item))
    }
    cancelEditComment()
  } catch (err) {
    commentMessage.value = err.message || '댓글을 수정하지 못했습니다.'
  } finally {
    commentSavingId.value = null
  }
}

const deleteOwnComment = async (comment) => {
  if (!game.value || commentDeletingId.value) return
  openCommentMenuId.value = null
  commentDeletingId.value = comment.id
  commentMessage.value = ''
  try {
    await gamesApi.deleteComment(game.value.id, comment.id)
    if (editingCommentId.value === comment.id) cancelEditComment()
    await loadComments(game.value.id, commentPage.value)
  } catch (err) {
    commentMessage.value = err.message || '댓글을 삭제하지 못했습니다.'
  } finally {
    commentDeletingId.value = null
  }
}

const changeCommentPage = async (nextPage) => {
  if (!game.value || commentLoading.value) return
  const targetPage = Math.min(commentTotalPages.value, Math.max(1, nextPage))
  if (targetPage === commentPage.value) return
  commentPage.value = targetPage
  await loadComments(game.value.id, targetPage)
}

const addWish = async () => {
  if (!game.value || wishlisted.value) return
  wishLoading.value = true
  wishMessage.value = ''
  try {
    const item = await wishlistApi.add(game.value.id)
    wishlisted.value = true
    wishlistItemId.value = item.id
    wishMessage.value = detailLabels.wishAdded
  } catch (err) {
    if (err.status === 401) {
      wishMessage.value = detailLabels.loginRequired
      router.push({ path: '/login', query: { next: route.fullPath } })
      return
    }
    wishMessage.value = err.message || detailLabels.wishAddError
  } finally {
    wishLoading.value = false
  }
}

const removeWish = async () => {
  if (!wishlistItemId.value) return
  wishLoading.value = true
  wishMessage.value = ''
  try {
    await wishlistApi.remove(wishlistItemId.value)
    wishlisted.value = false
    wishlistItemId.value = null
    wishMessage.value = detailLabels.wishRemoved
  } catch (err) {
    wishMessage.value = err.message || detailLabels.wishRemoveError
  } finally {
    wishLoading.value = false
  }
}

const toggleWish = () => {
  if (wishlisted.value) {
    removeWish()
  } else {
    addWish()
  }
}

onMounted(async () => {
  if (!auth.user) await auth.fetchMe()
  await loadGame(route.params.id)
})
watch(
  () => route.params.id,
  (id, oldId) => {
    if (id && id !== oldId) loadGame(id)
  },
)
</script>
