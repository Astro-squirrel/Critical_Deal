<template>
  <main class="login-page">
    <div class="login-wrap">
      <form class="login-card" @submit.prevent="submit">
        <h1 id="login-title">LOGIN</h1>

        <label class="login-field">
          <span>User Email</span>
          <input v-model="email" type="email" placeholder="이메일" autocomplete="email" required />
        </label>

        <label class="login-field">
          <span>Password</span>
          <div class="password-field">
            <input
              v-model="password"
              :type="passwordVisible ? 'text' : 'password'"
              placeholder="비밀번호"
              autocomplete="current-password"
              required
            />
            <button type="button" :aria-label="passwordVisible ? '비밀번호 숨기기' : '비밀번호 보기'" @click="passwordVisible = !passwordVisible">
              <Eye v-if="passwordVisible" :size="20" />
              <EyeOff v-else :size="20" />
            </button>
          </div>
        </label>

        <p v-if="loginError" class="login-error">
          <CircleAlert :size="14" />
          <span>{{ loginError }}</span>
        </p>

        <button class="login-primary" type="submit" :disabled="!canSubmit">
          {{ auth.loading ? '로그인 중...' : '로그인' }}
        </button>

        <div class="login-divider"><span>또는</span></div>

        <button type="button" class="steam-login-button login-steam" :disabled="steamLoading" @click="loginWithSteam">
          <img class="steam-logo" :src="steamLogo" alt="" />
          {{ steamLoading ? 'Steam으로 이동 중...' : 'Steam 계정으로 로그인' }}
        </button>
      </form>

      <p class="login-signup">
        Critical Deal이 처음이세요?
        <router-link to="/signup">회원 가입</router-link>
      </p>
    </div>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CircleAlert, Eye, EyeOff } from 'lucide-vue-next'
import { accountsApi } from '../api/accounts'
import steamLogo from '../assets/steam-logo.png'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const password = ref('')
const passwordVisible = ref(false)
const steamLoading = ref(false)
const steamError = ref('')
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const loginError = computed(() => steamError.value || route.query.steam_error || auth.error)
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const isEmailValid = computed(() => emailPattern.test(email.value.trim()))
const canSubmit = computed(() => !auth.loading && isEmailValid.value && password.value.trim().length > 0)

const submit = async () => {
  if (!canSubmit.value) return
  await auth.login({ email: email.value.trim(), password: password.value })
  router.push(route.query.next || '/')
}

const loginWithSteam = async () => {
  steamLoading.value = true
  steamError.value = ''
  try {
    const authUrl = await accountsApi.steamLoginUrl()
    window.location.assign(authUrl)
  } catch (error) {
    steamError.value = error.message
    steamLoading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: #191919;
  color: #d9d9d8;
  padding: 70px 24px 40px;
}

.login-wrap {
  width: min(100%, 350px);
  margin: 0 auto;
}

.login-card {
  display: grid;
  gap: 7px;
  padding: 30px 38px 22px;
}

.login-card h1 {
  margin: 0 0 12px;
  color: #d9d9d8;
  font-size: 38px;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: 0;
  text-align: center;
}

.login-field {
  display: grid;
}

.login-field > span {
  display: none;
}

.login-card input {
  width: 100%;
  height: 38px;
  border: 1px solid #333333;
  border-radius: 3px;
  background: #1f1f1f;
  color: #d9d9d8;
  font-size: 13px;
  outline: 0;
  padding: 0 10px;
}

.login-card input::placeholder {
  color: #777776;
}

.login-card input:focus {
  border-color: #3183d8;
  box-shadow: 0 0 0 1px #3183d8;
}

.password-field {
  position: relative;
}

.password-field input {
  padding-right: 44px;
}

.password-field button {
  position: absolute;
  top: 50%;
  right: 8px;
  min-height: 0;
  border: 0 !important;
  background: transparent !important;
  color: #3183d8 !important;
  padding: 5px 6px;
  font-size: 13px;
  font-weight: 800;
  transform: translateY(-50%);
}

.password-field button:hover {
  background: #252525 !important;
}

.login-primary {
  width: 100%;
  min-height: 30px;
  margin-top: 8px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 900;
}

.login-primary {
  border: 0 !important;
  background: #3183d8 !important;
  color: #ffffff !important;
}

.login-primary:disabled {
  background: rgba(49, 131, 216, 0.34) !important;
  color: rgba(255, 255, 255, 0.56) !important;
  cursor: not-allowed;
}

.login-primary:hover:not(:disabled) {
  background: #256db8 !important;
}

.login-divider {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 18px;
  color: #9ca3af;
  font-size: 13px;
  font-weight: 800;
  margin: 17px 0 13px;
}

.login-divider::before,
.login-divider::after {
  height: 1px;
  content: "";
  background: #333333;
}

button.steam-login-button.login-steam {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 24px;
  border: 0 !important;
  background: transparent !important;
  color: #d9d9d8 !important;
  font-size: 14px;
  font-weight: 900;
  padding: 0;
  box-shadow: none !important;
}

.steam-logo {
  display: block;
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
  border-radius: 50%;
  object-fit: cover;
}

button.steam-login-button.login-steam:hover:not(:disabled) {
  border: 0 !important;
  background: transparent !important;
  color: #ffffff !important;
  box-shadow: none !important;
}

button.steam-login-button.login-steam:disabled {
  border: 0 !important;
  background: transparent !important;
  color: #777776 !important;
  box-shadow: none !important;
}

.login-error {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 0;
  color: #ff1834 !important;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.2;
  white-space: nowrap;
}

.login-error svg {
  flex: 0 0 auto;
  color: #ff1834 !important;
}

.login-error span {
  overflow: hidden;
  text-overflow: ellipsis;
}

.login-signup {
  margin: 24px 0 0;
  color: #a3a3a2;
  text-align: center;
  font-size: 14px;
}

.login-signup a {
  color: #3183d8;
  font-weight: 900;
  text-decoration: none;
}

.login-signup a:hover {
  text-decoration: underline;
}

@media (max-width: 520px) {
  .login-page {
    padding: 32px 16px;
  }

  .login-card {
    padding: 0;
  }

  .login-card h1 {
    font-size: 34px;
  }
}
</style>
