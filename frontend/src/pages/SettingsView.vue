<template>
  <AppLayout>
    <section class="settings-page">
      <header class="settings-hero">
        <p class="eyebrow">SETTINGS</p>
        <h1>설정</h1>
        <p>{{ accountUser?.email || '로그인이 필요합니다.' }}</p>
      </header>

      <p v-if="message" class="profile-message">{{ message }}</p>
      <p v-if="loading" class="loading">설정을 불러오는 중...</p>

      <div v-if="auth.user" class="settings-shell">
        <aside class="settings-nav" aria-label="설정 메뉴">
          <div class="settings-nav-group">
            <button
              v-for="item in primaryMenu"
              :key="item.key"
              type="button"
              class="settings-nav-item"
              :class="{ active: activeSection === item.key }"
              @click="activeSection = item.key"
            >
              <component :is="item.icon" :size="18" />
              <span>{{ item.label }}</span>
            </button>
          </div>
        </aside>

        <section class="settings-content">
          <article v-if="activeSection === 'profile'" class="settings-content-panel">
            <div class="settings-panel-header">
              <h2>프로필</h2>
              <p>게임 화면에 표시되는 닉네임과 프로필 사진을 관리합니다.</p>
            </div>

            <div class="settings-block">
              <h3>프로필 사진</h3>
              <div class="settings-profile-card">
                <div class="settings-avatar-preview">
                  <img :src="profileAvatarPreview" :alt="profileForm.username || '프로필 사진'" />
                </div>
                <div class="settings-avatar-actions">
                  <label class="settings-avatar-action">
                    사진 선택
                    <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="selectAvatar" />
                  </label>
                  <span
                    class="settings-avatar-action"
                    :class="{ disabled: isDefaultAvatarSelected }"
                    role="button"
                    :aria-disabled="isDefaultAvatarSelected"
                    tabindex="0"
                    @click="setDefaultAvatar"
                    @keydown.enter.prevent="setDefaultAvatar"
                    @keydown.space.prevent="setDefaultAvatar"
                  >
                    기본 프로필로 설정
                  </span>
                  <p>jpg, png, webp, gif 파일을 3MB 이하로 업로드할 수 있습니다.</p>
                </div>
              </div>
            </div>

            <form class="settings-block settings-profile-form" @submit.prevent="saveProfileSettings">
              <label class="settings-field-row">
                <span>닉네임</span>
                <div class="settings-inline-field">
                  <input
                    v-model="profileForm.username"
                    class="settings-nickname-input"
                    type="text"
                    maxlength="150"
                    autocomplete="nickname"
                    @input="resetProfileUsernameCheck"
                  />
                  <button
                    type="button"
                    class="settings-inline-action settings-profile-submit"
                    :disabled="!canCheckProfileUsername || checkingUsername"
                    @click="checkProfileUsername"
                  >
                    {{ checkingUsername ? '확인 중...' : '중복 확인' }}
                  </button>
                  <button type="submit" class="settings-submit-button settings-profile-submit" :disabled="!canSaveProfile || saving">
                    {{ saving ? '저장 중...' : '프로필 저장' }}
                  </button>
                </div>
                <small
                  v-if="profileUsernameMessage"
                  :class="{ success: profileUsernameStatus === 'available' || profileUsernameStatus === 'same', error: profileUsernameStatus === 'unavailable' }"
                >
                  {{ profileUsernameMessage }}
                </small>
              </label>
            </form>
          </article>

          <article v-else-if="activeSection === 'account'" class="settings-content-panel">
            <div class="settings-panel-header">
              <h2>계정 및 로그인</h2>
              <p>계정 이메일과 보안 설정을 관리합니다.</p>
            </div>

            <div class="settings-block">
              <h3>이메일</h3>
              <p class="settings-info-box">계정 확인과 안내에 사용하는 이메일입니다.</p>
              <input class="settings-readonly-input" :value="accountUser?.email || '-'" readonly />
            </div>

            <div class="settings-block">
              <div class="settings-block-title">
                <h3>비밀번호</h3>
                <span>8자리 이상, 영문/숫자/특수문자 포함</span>
              </div>
              <button type="button" class="settings-inline-action settings-profile-submit" @click="openDialog('password')">비밀번호 변경</button>
            </div>

            <div class="settings-block settings-account-danger-block">
              <h3>회원탈퇴</h3>
              <p class="settings-info-box danger-info">계정, 위시리스트, 보유 게임 정보가 삭제됩니다.</p>
              <button type="button" class="settings-inline-action settings-profile-submit danger-action" @click="openDialog('delete')">회원탈퇴</button>
            </div>
          </article>

          <article v-else-if="activeSection === 'region'" class="settings-content-panel">
            <div class="settings-panel-header">
              <h2>지역</h2>
              <p>가격과 게임 정보 표시 기준입니다.</p>
            </div>

            <div class="settings-block">
              <h3>지역 및 통화</h3>
              <div class="settings-data-list">
                <div>
                  <span>국가</span>
                  <strong>대한민국</strong>
                </div>
                <div>
                  <span>통화</span>
                  <strong>KRW</strong>
                </div>
                <div>
                  <span>언어</span>
                  <strong>한국어</strong>
                </div>
              </div>
            </div>
          </article>
        </section>
      </div>

      <p v-else-if="!loading" class="profile-empty">설정을 보려면 로그인이 필요합니다.</p>
    </section>

    <div v-if="activeDialog" class="settings-modal-backdrop" @click.self="closeDialog">
      <section class="settings-modal" role="dialog" aria-modal="true" :aria-labelledby="`${activeDialog}-dialog-title`">
        <header class="settings-modal-header">
          <div>
            <p class="eyebrow">{{ activeDialog === 'password' ? 'PASSWORD' : 'DELETE ACCOUNT' }}</p>
            <h2 :id="`${activeDialog}-dialog-title`">{{ activeDialog === 'password' ? '비밀번호 변경' : '회원탈퇴' }}</h2>
          </div>
          <button type="button" class="settings-modal-close" aria-label="닫기" @click="closeDialog">닫기</button>
        </header>

        <form v-if="activeDialog === 'password'" class="settings-dialog-form" @submit.prevent="changePassword">
          <label v-if="requiresCurrentPassword">
            <span>현재 비밀번호</span>
            <input v-model="passwordForm.currentPassword" type="password" autocomplete="current-password" />
          </label>
          <label>
            <span>새 비밀번호</span>
            <input v-model="passwordForm.newPassword" type="password" autocomplete="new-password" />
            <small>8자리 이상, 영문/숫자/특수문자를 모두 포함해야 합니다.</small>
          </label>
          <label>
            <span>새 비밀번호 확인</span>
            <input v-model="passwordForm.newPasswordConfirm" type="password" autocomplete="new-password" />
          </label>
          <p v-if="dialogMessage" class="profile-message">{{ dialogMessage }}</p>
          <button type="submit" class="settings-submit-button settings-dialog-submit" :disabled="!canChangePassword || saving">
            {{ saving ? '변경 중...' : '비밀번호 변경' }}
          </button>
        </form>

        <form v-else class="settings-dialog-form danger-zone" @submit.prevent="deleteAccount">
          <p>회원탈퇴를 하면 계정, 위시리스트, 보유 게임 정보가 삭제됩니다. 이 작업은 되돌릴 수 없습니다.</p>
          <label>
            <span>확인 문구</span>
            <input v-model="deleteForm.confirmation" placeholder="회원탈퇴를 입력하세요" />
          </label>
          <label v-if="requiresCurrentPassword">
            <span>현재 비밀번호</span>
            <input v-model="deleteForm.password" type="password" autocomplete="current-password" />
          </label>
          <p v-if="dialogMessage" class="profile-message">{{ dialogMessage }}</p>
          <button type="submit" class="danger-button settings-dialog-submit" :disabled="!canDeleteAccount || saving">
            {{ saving ? '탈퇴 처리 중...' : '회원탈퇴' }}
          </button>
        </form>
      </section>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Globe2, LogIn, UserRound } from 'lucide-vue-next'
import { accountsApi } from '../api/accounts'
import defaultProfileAvatar from '../assets/default-profile.svg'
import AppLayout from '../layouts/AppLayout.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const profile = ref(null)
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const dialogMessage = ref('')
const activeDialog = ref('')
const activeSection = ref('profile')
const checkingUsername = ref(false)
const profileUsernameStatus = ref('')
const profileUsernameMessage = ref('')
const avatarPreviewUrl = ref('')
const avatarFile = ref(null)
const clearAvatar = ref(false)

const primaryMenu = [
  { key: 'profile', label: '프로필', icon: UserRound },
  { key: 'account', label: '계정 및 로그인', icon: LogIn },
  { key: 'region', label: '지역', icon: Globe2 },
]

const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  newPasswordConfirm: '',
})
const deleteForm = reactive({
  confirmation: '',
  password: '',
})
const profileForm = reactive({
  username: '',
})

const accountUser = computed(() => profile.value?.user || auth.user)
const originalUsername = computed(() => accountUser.value?.username || '')
const profileAvatarPreview = computed(() => avatarPreviewUrl.value || (clearAvatar.value ? defaultProfileAvatar : accountUser.value?.avatar_url || defaultProfileAvatar))
const isDefaultAvatarSelected = computed(() => !avatarFile.value && (clearAvatar.value || !accountUser.value?.avatar_url))
const isProfileUsernameChanged = computed(() => profileForm.username.trim() !== originalUsername.value)
const canCheckProfileUsername = computed(() => profileForm.username.trim().length >= 2 && isProfileUsernameChanged.value)
const canSaveProfile = computed(() => {
  const hasAvatarChange = Boolean(avatarFile.value) || clearAvatar.value
  const hasUsernameChange = isProfileUsernameChanged.value
  const usernameReady = !hasUsernameChange || profileUsernameStatus.value === 'available'
  return (hasAvatarChange || hasUsernameChange) && usernameReady
})
const requiresCurrentPassword = computed(() => accountUser.value?.has_usable_password !== false)
const isNewPasswordValid = computed(() => /^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/.test(passwordForm.newPassword))
const canChangePassword = computed(
  () =>
    (!requiresCurrentPassword.value || passwordForm.currentPassword.length > 0) &&
    isNewPasswordValid.value &&
    passwordForm.newPassword === passwordForm.newPasswordConfirm,
)
const canDeleteAccount = computed(
  () => deleteForm.confirmation.trim() === '회원탈퇴' && (!requiresCurrentPassword.value || deleteForm.password.length > 0),
)

const loadProfile = async () => {
  if (!auth.user) return
  profile.value = { user: auth.user }
  resetProfileForm()
  loading.value = false
  message.value = ''
}

const resetProfileForm = () => {
  profileForm.username = accountUser.value?.username || ''
  profileUsernameStatus.value = ''
  profileUsernameMessage.value = ''
  avatarFile.value = null
  avatarPreviewUrl.value = ''
  clearAvatar.value = false
}

const resetProfileUsernameCheck = () => {
  const username = profileForm.username.trim()
  if (username === originalUsername.value) {
    profileUsernameStatus.value = 'same'
    profileUsernameMessage.value = '현재 사용 중인 닉네임입니다.'
    return
  }
  profileUsernameStatus.value = ''
  profileUsernameMessage.value = ''
}

const checkProfileUsername = async () => {
  const username = profileForm.username.trim()
  if (!canCheckProfileUsername.value || checkingUsername.value) return
  checkingUsername.value = true
  profileUsernameMessage.value = ''
  try {
    const result = await accountsApi.checkUsername(username)
    profileUsernameStatus.value = result.available ? 'available' : 'unavailable'
    profileUsernameMessage.value = result.message
  } catch (error) {
    profileUsernameStatus.value = 'unavailable'
    profileUsernameMessage.value = error.message
  } finally {
    checkingUsername.value = false
  }
}

const selectAvatar = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  if (!['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(file.type)) {
    message.value = '프로필 사진은 jpg, png, webp, gif 파일만 사용할 수 있습니다.'
    event.target.value = ''
    return
  }
  if (file.size > 3 * 1024 * 1024) {
    message.value = '프로필 사진은 3MB 이하로 업로드해 주세요.'
    event.target.value = ''
    return
  }
  if (avatarPreviewUrl.value) URL.revokeObjectURL(avatarPreviewUrl.value)
  avatarFile.value = file
  clearAvatar.value = false
  avatarPreviewUrl.value = URL.createObjectURL(file)
  message.value = ''
}

const setDefaultAvatar = () => {
  if (isDefaultAvatarSelected.value) return
  if (avatarPreviewUrl.value) URL.revokeObjectURL(avatarPreviewUrl.value)
  avatarFile.value = null
  avatarPreviewUrl.value = ''
  clearAvatar.value = Boolean(accountUser.value?.avatar_url)
}

const saveProfileSettings = async () => {
  if (!canSaveProfile.value || saving.value) return
  saving.value = true
  message.value = ''
  try {
    const formData = new FormData()
    formData.append('username', profileForm.username.trim())
    if (avatarFile.value) formData.append('avatar', avatarFile.value)
    if (clearAvatar.value) formData.append('clear_avatar', '1')
    const user = await accountsApi.updateProfile(formData)
    auth.user = user
    profile.value = { user }
    resetProfileForm()
    message.value = '프로필이 저장되었습니다.'
  } catch (error) {
    message.value = error.message
  } finally {
    saving.value = false
  }
}

const resetForms = () => {
  passwordForm.currentPassword = ''
  passwordForm.newPassword = ''
  passwordForm.newPasswordConfirm = ''
  deleteForm.confirmation = ''
  deleteForm.password = ''
  dialogMessage.value = ''
}

const openDialog = (dialog) => {
  resetForms()
  activeDialog.value = dialog
}

const closeDialog = () => {
  activeDialog.value = ''
  resetForms()
}

const changePassword = async () => {
  if (!canChangePassword.value) return
  saving.value = true
  dialogMessage.value = ''
  try {
    await accountsApi.changePassword({
      current_password: passwordForm.currentPassword,
      new_password: passwordForm.newPassword,
      new_password_confirm: passwordForm.newPasswordConfirm,
    })
    auth.user = null
    router.push('/login')
  } catch (error) {
    dialogMessage.value = error.message
  } finally {
    saving.value = false
  }
}

const deleteAccount = async () => {
  if (!canDeleteAccount.value) return
  saving.value = true
  dialogMessage.value = ''
  try {
    await accountsApi.deleteAccount({
      confirmation: deleteForm.confirmation.trim(),
      password: deleteForm.password,
    })
    auth.user = null
    router.push('/')
  } catch (error) {
    dialogMessage.value = error.message
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (!auth.user) await auth.fetchMe()
  await loadProfile()
})
</script>
