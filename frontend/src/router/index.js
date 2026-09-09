import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import ReaderLoginView from '../views/ReaderLoginView.vue'
import StaffLoginView from '../views/StaffLoginView.vue'
import WriterDashboard from '../views/WriterDashboard.vue'
import ArticleComposeView from '../views/ArticleComposeView.vue'
import EditorDashboard from '../views/EditorDashboard.vue'
import ArticleReviewView from '../views/ArticleReviewView.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: ReaderLoginView },
  { path: '/staff/login', component: StaffLoginView },
  { path: '/writer', component: WriterDashboard, meta: { requiresAuth: true } },
  { path: '/writer/compose', component: ArticleComposeView, meta: { requiresAuth: true } },
  { path: '/writer/compose/:id', component: ArticleComposeView, meta: { requiresAuth: true } },
  { path: '/editor', component: EditorDashboard, meta: { requiresAuth: true } },
  { path: '/editor/review/:id', component: ArticleReviewView, meta: { requiresAuth: true } },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) return '/staff/login'
  return true
})

export default router
