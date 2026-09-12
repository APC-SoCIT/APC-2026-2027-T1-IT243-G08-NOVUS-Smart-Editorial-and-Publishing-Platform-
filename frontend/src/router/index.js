import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import ReaderLoginView from '../views/ReaderLoginView.vue'
import ReaderRegisterView from '../views/ReaderRegisterView.vue'
import StaffLoginView from '../views/StaffLoginView.vue'
import WriterDashboard from '../views/WriterDashboard.vue'
import ArticleComposeView from '../views/ArticleComposeView.vue'
import EditorDashboard from '../views/EditorDashboard.vue'
import ReportsView from '../views/ReportsView.vue'
import ArchiveView from '../views/ArchiveView.vue'
import IssuesOverview from '../views/IssuesOverview.vue'
import CalendarView from '../views/CalendarView.vue'
import NotificationSettings from '../views/NotificationSettings.vue'
import PlatformSettings from '../views/PlatformSettings.vue'
import ArticleReviewView from '../views/ArticleReviewView.vue'
import PublisherDashboard from '../views/PublisherDashboard.vue'
import IssueDetailView from '../views/IssueDetailView.vue'
import DesignerDashboard from '../views/DesignerDashboard.vue'
import DesignerArticleView from '../views/DesignerArticleView.vue'
import ReaderHome from '../views/ReaderHome.vue'
import ReaderArticle from '../views/ReaderArticle.vue'
import IssueArchive from '../views/IssueArchive.vue'
import AboutView from '../views/AboutView.vue'
import LegalView from '../views/LegalView.vue'
import IssueReader from '../views/IssueReader.vue'

const routes = [
  { path: '/', redirect: '/read' },
  { path: '/login', component: ReaderLoginView },
  { path: '/register', component: ReaderRegisterView },
  { path: '/staff/login', component: StaffLoginView },
  { path: '/writer', component: WriterDashboard, meta: { requiresAuth: true } },
  { path: '/writer/compose', component: ArticleComposeView, meta: { requiresAuth: true } },
  { path: '/writer/compose/:id', component: ArticleComposeView, meta: { requiresAuth: true } },
  // Editors write too. Same composer, a path that does not imply otherwise.
  { path: '/compose', component: ArticleComposeView, meta: { requiresAuth: true } },
  { path: '/compose/:id', component: ArticleComposeView, meta: { requiresAuth: true } },
  { path: '/editor', component: EditorDashboard, meta: { requiresAuth: true } },
  { path: '/calendar', component: CalendarView, meta: { requiresAuth: true } },
  { path: '/notifications', component: NotificationSettings, meta: { requiresAuth: true } },
  { path: '/issues-overview', component: IssuesOverview, meta: { requiresAuth: true } },
  { path: '/archive', component: ArchiveView, meta: { requiresAuth: true } },
  { path: '/reports', component: ReportsView, meta: { requiresAuth: true } },
  { path: '/settings', component: PlatformSettings, meta: { requiresAuth: true } },
  { path: '/editor/review/:id', component: ArticleReviewView, meta: { requiresAuth: true } },
  { path: '/publisher', component: PublisherDashboard, meta: { requiresAuth: true } },
  { path: '/publisher/issue/:id', component: IssueDetailView, meta: { requiresAuth: true } },
  { path: '/designer', component: DesignerDashboard, meta: { requiresAuth: true } },
  { path: '/designer/article/:id', component: DesignerArticleView, meta: { requiresAuth: true } },
  { path: '/read', component: ReaderHome },
  { path: '/read/:id', component: ReaderArticle },
  { path: '/issues', component: IssueArchive },
  { path: '/about', component: AboutView },
  { path: '/legal/:doc', component: LegalView },
  { path: '/legal', redirect: '/legal/privacy' },
  { path: '/issues/:id', component: IssueReader },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) return '/staff/login'
  return true
})

export default router
