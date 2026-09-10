import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import ReaderLoginView from '../views/ReaderLoginView.vue'
import StaffLoginView from '../views/StaffLoginView.vue'
import WriterDashboard from '../views/WriterDashboard.vue'
import ArticleComposeView from '../views/ArticleComposeView.vue'
import EditorDashboard from '../views/EditorDashboard.vue'
import ArticleReviewView from '../views/ArticleReviewView.vue'
import PublisherDashboard from '../views/PublisherDashboard.vue'
import IssueDetailView from '../views/IssueDetailView.vue'
import DesignerDashboard from '../views/DesignerDashboard.vue'
import DesignerArticleView from '../views/DesignerArticleView.vue'
import ReaderHome from '../views/ReaderHome.vue'
import ReaderArticle from '../views/ReaderArticle.vue'

const routes = [
  { path: '/', redirect: '/read' },
  { path: '/login', component: ReaderLoginView },
  { path: '/staff/login', component: StaffLoginView },
  { path: '/writer', component: WriterDashboard, meta: { requiresAuth: true } },
  { path: '/writer/compose', component: ArticleComposeView, meta: { requiresAuth: true } },
  { path: '/writer/compose/:id', component: ArticleComposeView, meta: { requiresAuth: true } },
  { path: '/editor', component: EditorDashboard, meta: { requiresAuth: true } },
  { path: '/editor/review/:id', component: ArticleReviewView, meta: { requiresAuth: true } },
  { path: '/publisher', component: PublisherDashboard, meta: { requiresAuth: true } },
  { path: '/publisher/issue/:id', component: IssueDetailView, meta: { requiresAuth: true } },
  { path: '/designer', component: DesignerDashboard, meta: { requiresAuth: true } },
  { path: '/designer/article/:id', component: DesignerArticleView, meta: { requiresAuth: true } },
  { path: '/read', component: ReaderHome },
  { path: '/read/:id', component: ReaderArticle },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) return '/staff/login'
  return true
})

export default router
