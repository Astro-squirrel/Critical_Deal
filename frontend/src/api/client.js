import axios from 'axios'

const apiBaseURL = () => {
  const explicitBaseURL = import.meta.env.VITE_API_BASE_URL
  if (explicitBaseURL) return explicitBaseURL.replace(/\/$/, '')

  const apiHost = import.meta.env.VITE_API_HOST
  if (apiHost) {
    const normalizedHost = apiHost.replace(/^https?:\/\//, '').replace(/\/$/, '')
    return `https://${normalizedHost}/api`
  }

  return 'http://127.0.0.1:8000/api'
}

export const api = axios.create({
  baseURL: apiBaseURL(),
  withCredentials: true,
  timeout: 20000,
})

let csrfToken = ''

const readCookie = (name) =>
  document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`))
    ?.split('=')[1]

const ensureCsrfToken = async () => {
  csrfToken = readCookie('csrftoken') ? decodeURIComponent(readCookie('csrftoken')) : csrfToken
  if (csrfToken) return csrfToken

  const response = await api.get('/accounts/csrf/')
  csrfToken = response.data?.data?.csrf_token || ''
  return csrfToken
}

api.interceptors.request.use(async (config) => {
  const method = config.method?.toUpperCase()
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const token = await ensureCsrfToken()
    if (token) config.headers['X-CSRFToken'] = token
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const data = error.response?.data
    const isTimeout = error.code === 'ECONNABORTED'
    if (isTimeout && !String(error.config?.url || '').includes('/ai-analysis/')) {
      const apiError = new Error('요청 시간이 오래 걸리고 있어요. 잠시 후 다시 시도해 주세요.')
      apiError.status = error.response?.status
      apiError.details = data?.details || data
      return Promise.reject(apiError)
    }
    const message =
      (isTimeout && '분석 요청이 오래 걸리고 있어요. 잠시 후 다시 시도하면 저장된 결과를 불러올 수 있습니다.') ||
      data?.message ||
      data?.detail ||
      data?.non_field_errors?.[0] ||
      '요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.'
    const apiError = new Error(message)
    apiError.status = error.response?.status
    apiError.details = data?.details || data
    return Promise.reject(apiError)
  },
)
