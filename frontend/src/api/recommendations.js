import { api } from './client'

export const recommendationsApi = {
  personalized: () => api.get('/recommendations/personalized/').then((r) => r.data.data),
  homePersonalized: (limit = 3) => api.get('/recommendations/personalized/home/', { params: { limit } }).then((r) => r.data.data),
  chat: (message, history = []) => api.post('/recommendations/chat/', { message, history }).then((r) => r.data.data),
}

