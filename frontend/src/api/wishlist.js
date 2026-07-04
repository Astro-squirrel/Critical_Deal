import { api } from './client'

export const wishlistApi = {
  list: () => api.get('/wishlist/').then((r) => r.data.data),
  add: (game_id) => api.post('/wishlist/', { game_id }).then((r) => r.data.data),
  remove: (id) => api.delete(`/wishlist/${id}/`).then((r) => r.data.data),
}

