import { api } from './client'

export const accountsApi = {
  signup: (payload) => api.post('/accounts/signup/', payload).then((r) => r.data.data),
  checkEmail: (email) => api.get('/accounts/email/check/', { params: { email } }).then((r) => r.data.data),
  sendEmailCode: (email) => api.post('/accounts/email/code/', { email }).then((r) => r.data),
  verifyEmailCode: (email, code) => api.post('/accounts/email/code/verify/', { email, code }).then((r) => r.data),
  checkUsername: (username) => api.get('/accounts/username/check/', { params: { username } }).then((r) => r.data.data),
  login: (payload) => api.post('/accounts/login/', payload).then((r) => r.data.data),
  steamLoginUrl: () => api.get('/accounts/steam/login/').then((r) => r.data.data.auth_url),
  logout: () => api.post('/accounts/logout/').then((r) => r.data.data),
  me: () => api.get('/accounts/me/').then((r) => r.data.data),
  deleteAccount: (payload) => api.delete('/accounts/me/delete/', { data: payload }).then((r) => r.data.data),
  changePassword: (payload) => api.post('/accounts/me/password/', payload).then((r) => r.data.data),
  updateProfile: (payload) => api.patch('/accounts/me/profile/', payload).then((r) => r.data.data),
  profile: () => api.get('/accounts/profile/').then((r) => r.data.data),
  addOwnedGame: (payload) => api.post('/accounts/owned-games/', payload).then((r) => r.data.data),
  removeOwnedGame: (id) => api.delete(`/accounts/owned-games/${id}/`).then((r) => r.data.data),
  connectSteam: (steam_id_or_url) => api.post('/accounts/steam/connect/', { steam_id_or_url }).then((r) => r.data.data),
}

