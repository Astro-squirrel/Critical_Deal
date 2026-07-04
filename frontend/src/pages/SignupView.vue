<template>
  <main class="signup-page">
    <form class="signup-form" @submit.prevent="submit">
      <h1>SIGN UP</h1>

      <label class="field-group">
        <span>이메일</span>
        <span class="field-hint">이메일 형식으로 입력해 주세요. 예: player@example.com</span>
        <span class="validated-input">
          <input v-model="email" type="email" placeholder="이메일" required />
          <span class="status-light" :class="emailStatusClass"></span>
        </span>
        <span v-if="emailMessage" class="field-message" :class="{ success: emailAvailable, error: emailChecked && !emailAvailable }">
          {{ emailMessage }}
        </span>
      </label>

      <label class="field-group">
        <span>이메일 인증</span>
        <span class="email-code-row">
          <input v-model="emailCode" inputmode="numeric" maxlength="6" placeholder="6자리 인증코드" :disabled="emailCodeVerified" />
          <button type="button" class="check-button" :disabled="!canSendEmailCode || sendingEmailCode" @click="sendEmailCode">
            {{ sendingEmailCode ? '발송 중' : emailCodeSent ? '다시 보내기' : '코드 보내기' }}
          </button>
          <button type="button" class="check-button verify-button" :disabled="!canVerifyEmailCode || verifyingEmailCode" @click="verifyEmailCode">
            {{ verifyingEmailCode ? '확인 중' : emailCodeVerified ? '인증 완료' : '인증 확인' }}
          </button>
        </span>
        <span v-if="emailCodeMessage || emailCodeCountdownMessage" class="email-code-feedback">
          <span v-if="emailCodeMessage" class="field-message email-code-message" :class="emailCodeMessageTone">
            {{ emailCodeMessage }}
          </span>
          <span v-if="emailCodeCountdownMessage" class="field-message countdown-message" :class="{ error: emailCodeSecondsLeft <= 0 }">
            {{ emailCodeCountdownMessage }}
          </span>
        </span>
      </label>

      <label class="field-group">
        <span>닉네임</span>
        <span class="nickname-row">
          <input v-model="username" placeholder="닉네임" @input="resetUsernameCheck" />
          <button type="button" class="check-button" :disabled="!canCheckUsername || checkingUsername" @click="checkUsername">
            {{ checkingUsername ? '확인 중' : '중복 확인' }}
          </button>
        </span>
        <span v-if="usernameMessage" class="field-message" :class="{ success: usernameAvailable, error: usernameChecked && !usernameAvailable }">
          {{ usernameMessage }}
        </span>
      </label>

      <label class="field-group">
        <span>비밀번호</span>
        <span class="field-hint password-rules">8자리 이상, 영문/숫자/특수문자를 모두 포함해야 합니다.</span>
        <span class="validated-input password-input">
          <input v-model="password" :type="showPassword ? 'text' : 'password'" placeholder="비밀번호" required />
          <button type="button" class="password-eye" :aria-label="showPassword ? '비밀번호 숨기기' : '비밀번호 보기'" @click="showPassword = !showPassword">
            <Eye v-if="showPassword" :size="18" />
            <EyeOff v-else :size="18" />
          </button>
          <span class="status-light" :class="passwordStatusClass"></span>
        </span>
      </label>

      <label class="field-group">
        <span>비밀번호 확인</span>
        <span class="validated-input password-input">
          <input v-model="passwordConfirm" :type="showPasswordConfirm ? 'text' : 'password'" placeholder="비밀번호 다시 입력" required />
          <button
            type="button"
            class="password-eye"
            :aria-label="showPasswordConfirm ? '비밀번호 확인 숨기기' : '비밀번호 확인 보기'"
            @click="showPasswordConfirm = !showPasswordConfirm"
          >
            <Eye v-if="showPasswordConfirm" :size="18" />
            <EyeOff v-else :size="18" />
          </button>
          <span class="status-light" :class="passwordConfirmStatusClass"></span>
        </span>
        <span v-if="passwordConfirmMessage" class="field-message" :class="{ success: isPasswordConfirmValid, error: !isPasswordConfirmValid }">
          {{ passwordConfirmMessage }}
        </span>
      </label>

      <p v-if="error" class="signup-error">
        <CircleAlert :size="14" />
        <span>{{ error }}</span>
      </p>
      <button class="signup-primary" type="submit" :disabled="!canSubmit">가입하기</button>
      <router-link class="signup-login-link" to="/login">이미 계정이 있어요</router-link>
    </form>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { CircleAlert, Eye, EyeOff } from 'lucide-vue-next'
import { accountsApi } from '../api/accounts'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const emailCode = ref('')
const username = ref('')
const password = ref('')
const passwordConfirm = ref('')
const showPassword = ref(false)
const showPasswordConfirm = ref(false)
const emailAvailable = ref(false)
const emailChecked = ref(false)
const emailMessage = ref('')
const checkingEmail = ref(false)
const sendingEmailCode = ref(false)
const verifyingEmailCode = ref(false)
const emailCodeSent = ref(false)
const emailCodeVerified = ref(false)
const emailCodeMessage = ref('')
const emailCodeMessageTone = ref('')
const emailCodeSecondsLeft = ref(0)
const usernameAvailable = ref(false)
const usernameChecked = ref(false)
const usernameMessage = ref('')
const checkingUsername = ref(false)
const error = ref('')
const auth = useAuthStore()
const router = useRouter()

let emailCheckTimer = null
let emailCodeTimer = null

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const isEmailTouched = computed(() => email.value.length > 0)
const isEmailValid = computed(() => emailPattern.test(email.value.trim()))
const isPasswordTouched = computed(() => password.value.length > 0)
const isPasswordValid = computed(() => /^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/.test(password.value))
const isPasswordConfirmTouched = computed(() => passwordConfirm.value.length > 0)
const isPasswordConfirmValid = computed(() => passwordConfirm.value.length > 0 && passwordConfirm.value === password.value)
const passwordConfirmMessage = computed(() => {
  if (!isPasswordConfirmTouched.value) return ''
  return isPasswordConfirmValid.value ? '비밀번호가 일치합니다.' : '비밀번호가 일치하지 않습니다.'
})
const canCheckUsername = computed(() => username.value.trim().length >= 2)
const canSendEmailCode = computed(() => isEmailValid.value && emailAvailable.value && !checkingEmail.value && !emailCodeVerified.value)
const canVerifyEmailCode = computed(
  () => isEmailValid.value && emailCodeSent.value && emailCodeSecondsLeft.value > 0 && emailCode.value.trim().length === 6 && !emailCodeVerified.value,
)
const canSubmit = computed(
  () =>
    isEmailValid.value &&
    emailAvailable.value &&
    emailCode.value.trim().length === 6 &&
    emailCodeVerified.value &&
    isPasswordValid.value &&
    isPasswordConfirmValid.value &&
    usernameAvailable.value &&
    !checkingEmail.value &&
    !sendingEmailCode.value &&
    !checkingUsername.value,
)
const emailCodeCountdownText = computed(() => {
  const seconds = Math.max(0, emailCodeSecondsLeft.value)
  const minutes = String(Math.floor(seconds / 60)).padStart(2, '0')
  const remainingSeconds = String(seconds % 60).padStart(2, '0')
  return `${minutes}:${remainingSeconds}`
})
const emailCodeCountdownMessage = computed(() => {
  if (!emailCodeSent.value || emailCodeVerified.value) return ''
  if (emailCodeSecondsLeft.value <= 0) return '시간 만료'
  return `남은 시간 ${emailCodeCountdownText.value}`
})

const emailStatusClass = computed(() => ({
  valid: isEmailTouched.value && isEmailValid.value && emailAvailable.value,
  invalid: isEmailTouched.value && (!isEmailValid.value || (emailChecked.value && !emailAvailable.value)),
}))

const passwordStatusClass = computed(() => ({
  valid: isPasswordTouched.value && isPasswordValid.value,
  invalid: isPasswordTouched.value && !isPasswordValid.value,
}))

const passwordConfirmStatusClass = computed(() => ({
  valid: isPasswordConfirmTouched.value && isPasswordConfirmValid.value,
  invalid: isPasswordConfirmTouched.value && !isPasswordConfirmValid.value,
}))

const clearEmailCodeCountdown = () => {
  if (emailCodeTimer) {
    window.clearInterval(emailCodeTimer)
    emailCodeTimer = null
  }
  emailCodeSecondsLeft.value = 0
}

const startEmailCodeCountdown = (seconds = 600) => {
  clearEmailCodeCountdown()
  const expiresAt = Date.now() + Number(seconds || 600) * 1000
  const updateCountdown = () => {
    emailCodeSecondsLeft.value = Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000))
    if (emailCodeSecondsLeft.value <= 0 && emailCodeTimer) {
      window.clearInterval(emailCodeTimer)
      emailCodeTimer = null
    }
  }
  updateCountdown()
  emailCodeTimer = window.setInterval(updateCountdown, 1000)
}

const resetEmailCheck = () => {
  emailAvailable.value = false
  emailChecked.value = false
  emailMessage.value = ''
  emailCode.value = ''
  emailCodeSent.value = false
  emailCodeVerified.value = false
  emailCodeMessage.value = ''
  emailCodeMessageTone.value = ''
  clearEmailCodeCountdown()
}

const checkEmail = async () => {
  if (!isEmailValid.value) {
    emailAvailable.value = false
    emailChecked.value = true
    emailMessage.value = isEmailTouched.value ? '올바른 이메일 형식이 아닙니다.' : ''
    return
  }

  checkingEmail.value = true
  emailChecked.value = false
  emailMessage.value = '이메일 중복 확인 중...'
  try {
    const result = await accountsApi.checkEmail(email.value.trim())
    emailAvailable.value = result.available
    emailMessage.value = result.message
  } catch (checkError) {
    emailAvailable.value = false
    emailMessage.value = checkError.message
  } finally {
    emailChecked.value = true
    checkingEmail.value = false
  }
}

const sendEmailCode = async () => {
  if (!canSendEmailCode.value) return
  sendingEmailCode.value = true
  emailCodeMessage.value = ''
  emailCodeMessageTone.value = ''
  try {
    const result = await accountsApi.sendEmailCode(email.value.trim())
    emailCodeSent.value = true
    emailCodeVerified.value = false
    emailCodeMessage.value = result.message || '인증코드를 이메일로 보냈습니다.'
    emailCodeMessageTone.value = 'neutral'
    startEmailCodeCountdown(result.data?.expires_in_seconds || 600)
  } catch (sendError) {
    emailCodeSent.value = false
    emailCodeMessage.value = sendError.message
    emailCodeMessageTone.value = 'error'
    clearEmailCodeCountdown()
  } finally {
    sendingEmailCode.value = false
  }
}

watch(email, () => {
  resetEmailCheck()
  window.clearTimeout(emailCheckTimer)
  emailCheckTimer = window.setTimeout(checkEmail, 450)
})

const resetUsernameCheck = () => {
  usernameAvailable.value = false
  usernameChecked.value = false
  usernameMessage.value = ''
}

const checkUsername = async () => {
  if (!canCheckUsername.value) return
  checkingUsername.value = true
  usernameChecked.value = false
  usernameMessage.value = ''
  try {
    const result = await accountsApi.checkUsername(username.value.trim())
    usernameAvailable.value = result.available
    usernameMessage.value = result.message
  } catch (checkError) {
    usernameAvailable.value = false
    usernameMessage.value = checkError.message
  } finally {
    usernameChecked.value = true
    checkingUsername.value = false
  }
}

const submit = async () => {
  error.value = ''
  if (!canSubmit.value) {
    error.value = '이메일 인증, 닉네임 중복 확인, 비밀번호 형식을 확인해 주세요.'
    return
  }

  try {
    await auth.signup({
      email: email.value.trim(),
      email_verification_code: emailCode.value.trim(),
      username: username.value.trim(),
      password: password.value,
    })
    router.push('/')
  } catch (signupError) {
    error.value = signupError.message
  }
}

const verifyEmailCode = async () => {
  if (!canVerifyEmailCode.value) return
  verifyingEmailCode.value = true
  emailCodeMessage.value = ''
  emailCodeMessageTone.value = ''
  try {
    const result = await accountsApi.verifyEmailCode(email.value.trim(), emailCode.value.trim())
    emailCodeVerified.value = Boolean(result.data?.verified)
    emailCodeMessage.value = result.message || '이메일 인증이 완료되었습니다.'
    emailCodeMessageTone.value = emailCodeVerified.value ? 'success' : 'neutral'
    if (emailCodeVerified.value) clearEmailCodeCountdown()
  } catch (verifyError) {
    emailCodeVerified.value = false
    emailCodeMessage.value = verifyError.message
    emailCodeMessageTone.value = 'error'
  } finally {
    verifyingEmailCode.value = false
  }
}

watch(emailCode, () => {
  if (!emailCodeVerified.value) return
  emailCodeVerified.value = false
})

onBeforeUnmount(() => {
  window.clearTimeout(emailCheckTimer)
  clearEmailCodeCountdown()
})
</script>

<style scoped>
.signup-page {
  min-height: 100vh;
  background: #191919;
  color: #d9d9d8;
  padding: 34px 24px 48px;
}

.signup-form {
  display: grid;
  gap: 18px;
  width: min(100%, 460px);
  margin: 0 auto;
  padding: 18px 30px 24px;
}

.signup-form h1 {
  margin: 0 0 16px;
  color: #d9d9d8;
  font-size: 38px;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: 0;
  text-align: center;
}

.field-group {
  display: grid;
  gap: 8px;
}

.field-group > span:first-child {
  display: block;
  color: #d9d9d8 !important;
  font-size: 14px;
  font-weight: 900;
  line-height: 1.2;
}

.field-hint {
  display: block;
  margin-top: -3px;
  color: #8d8d8c !important;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.25;
}

.password-rules {
  display: grid;
  gap: 2px;
}

.signup-form input {
  width: 100%;
  height: 48px;
  border: 0;
  border-bottom: 1px solid #3d3d3d;
  border-radius: 0;
  background: transparent;
  color: #d9d9d8;
  font-size: 13px;
  outline: 0;
  padding: 0 4px;
}

.signup-form input:disabled {
  color: #777776;
  cursor: not-allowed;
}

.signup-form input::placeholder {
  color: #777776;
}

.signup-form input:focus {
  border: 0 !important;
  border-bottom: 1px solid #3183d8 !important;
  box-shadow: none !important;
}

.validated-input,
.password-input {
  position: relative;
  display: block;
}

.validated-input input {
  padding-right: 34px;
}

.password-input input {
  padding-right: 64px;
}

button.password-eye {
  position: absolute;
  top: 50%;
  right: 28px;
  min-height: 0;
  border: 0 !important;
  background: transparent !important;
  color: #3183d8 !important;
  padding: 5px 6px;
  transform: translateY(-50%);
  box-shadow: none !important;
}

button.password-eye:hover,
button.password-eye:focus,
button.password-eye:focus-visible {
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  outline: 0;
}

.status-light {
  position: absolute;
  top: 50%;
  right: 10px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #555555;
  transform: translateY(-50%);
}

.status-light.valid {
  background: #24d481;
}

.status-light.invalid {
  background: #ff1834;
}

.nickname-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 104px;
  gap: 10px;
}

.email-code-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 94px 94px;
  gap: 8px;
}

.check-button {
  min-width: 0;
  min-height: 48px;
  border: 0 !important;
  border-radius: 4px;
  background: #3183d8 !important;
  color: #ffffff !important;
  padding: 0 8px;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.check-button:disabled {
  background: rgba(49, 131, 216, 0.34) !important;
  color: rgba(255, 255, 255, 0.56) !important;
  cursor: not-allowed;
}

.verify-button:not(:disabled) {
  background: #256db8 !important;
}

.field-message {
  overflow: hidden;
  color: #a3a3a2 !important;
  font-size: 11px;
  font-weight: 800;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.field-message.success {
  color: #24d481 !important;
}

.field-message.error {
  color: #ff1834 !important;
}

.email-code-feedback {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 14px;
}

.field-message.email-code-message {
  color: #ffffff !important;
}

.field-message.email-code-message.success {
  color: #24d481 !important;
}

.field-message.email-code-message.error {
  color: #ff1834 !important;
}

.countdown-message {
  justify-self: end;
  color: #8d8d8c !important;
}

.signup-error {
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

.signup-error svg {
  flex: 0 0 auto;
  color: #ff1834 !important;
}

.signup-error span {
  overflow: hidden;
  color: #ff1834 !important;
  text-overflow: ellipsis;
}

.signup-primary {
  width: 100%;
  min-height: 46px;
  margin-top: 6px;
  border: 0 !important;
  border-radius: 4px;
  background: #3183d8 !important;
  color: #ffffff !important;
  font-size: 14px;
  font-weight: 900;
}

.signup-primary:disabled {
  background: rgba(49, 131, 216, 0.34) !important;
  color: rgba(255, 255, 255, 0.56) !important;
  cursor: not-allowed;
}

.signup-login-link {
  margin-top: 0;
  color: #3183d8 !important;
  font-size: 14px;
  font-weight: 900;
  text-align: center;
  text-decoration: none;
}

.signup-login-link:hover {
  text-decoration: underline;
}

@media (max-width: 520px) {
  .signup-page {
    padding: 32px 16px;
  }

  .signup-form {
    gap: 16px;
    padding: 0;
  }

  .signup-form h1 {
    font-size: 34px;
  }

  .nickname-row,
  .email-code-row {
    grid-template-columns: 1fr;
  }
}
</style>
