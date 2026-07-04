import { api } from './client'

export const gamesApi = {
  search: (q) => api.get('/games/search/', { params: { q } }).then((r) => r.data.data),
  suggest: (q) => api.get('/games/search/', { params: { q, suggest: 1, include_dlc: 1 } }).then((r) => r.data.data),
  list: (params = {}) => api.get('/games/', { params }).then((r) => r.data.data || r.data.results?.data || r.data.results),
  listPage: (params = {}) => api.get('/games/', { params }).then((r) => r.data),
  popularDiscounts: (limit = 10) =>
    api
      .get('/games/', { params: { ordering: '-steam_review_count', discounted: 1, page_size: limit } })
      .then((r) => r.data.results?.data || []),
  genres: () => api.get('/games/genres/').then((r) => r.data.data),
  detail: (id) => api.get(`/games/${id}/`).then((r) => r.data.data),
  otherPrices: (id) => api.get(`/games/${id}/other-prices/`).then((r) => r.data.data),
  relatedProducts: (id) => api.get(`/games/${id}/related-products/`).then((r) => r.data.data),
  comments: (id, params = {}) => api.get(`/games/${id}/comments/`, { params }).then((r) => r.data.data),
  userComments: (userId, params = {}) => api.get(`/games/comments/users/${userId}/`, { params }).then((r) => r.data.data),
  addComment: (id, payload) => api.post(`/games/${id}/comments/`, payload).then((r) => r.data.data),
  updateComment: (id, commentId, payload) => api.patch(`/games/${id}/comments/${commentId}/`, payload).then((r) => r.data.data),
  deleteComment: (id, commentId) => api.delete(`/games/${id}/comments/${commentId}/`).then((r) => r.data.data),
  reactComment: (id, commentId, reaction) =>
    api.post(`/games/${id}/comments/${commentId}/reaction/`, { reaction }).then((r) => r.data.data),
  history: (id) => api.get(`/games/${id}/history/`).then((r) => r.data.data),
  recommendation: (id) => api.get(`/games/${id}/recommendation/`).then((r) => r.data.data),
  aiAnalysis: (id) => api.post(`/games/${id}/ai-analysis/`, null, { timeout: 120000 }).then((r) => r.data.data),
  popular: () => api.get('/deals/popular/').then((r) => r.data.data),
  best: () => api.get('/deals/best/').then((r) => r.data.data),
  epicFree: () => api.get('/epic/free-games/').then((r) => r.data.data),
}

