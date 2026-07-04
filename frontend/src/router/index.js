import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'home', component: () => import('../pages/HomeView.vue') },
  { path: '/login', name: 'login', component: () => import('../pages/LoginView.vue') },
  { path: '/signup', name: 'signup', component: () => import('../pages/SignupView.vue') },
  { path: '/games', name: 'games', component: () => import('../pages/GameListView.vue') },
  { path: '/free-games', name: 'free-games', component: () => import('../pages/FreeGamesView.vue') },
  { path: '/games/:id', name: 'game-detail', component: () => import('../pages/GameDetailView.vue') },
  { path: '/users/:id/comments', name: 'user-comments', component: () => import('../pages/UserCommentsView.vue') },
  { path: '/profile', name: 'profile', component: () => import('../pages/ProfileView.vue') },
  { path: '/settings', name: 'settings', component: () => import('../pages/SettingsView.vue') },
  { path: '/wishlist', name: 'wishlist', component: () => import('../pages/WishlistView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

