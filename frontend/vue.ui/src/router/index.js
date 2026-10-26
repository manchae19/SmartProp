import { createRouter, createWebHistory } from 'vue-router'

import LoginView from '../components/LoginView.vue'
import RegisterView from '../components/RegisterView.vue'

// USER
import HomeView from '../../user/views/HomeView.vue'
import PostView from '../../user/views/PostView.vue'
import PostStep2View from '../../user/views/PostStep2View.vue'
import PostStep3View from '../../user/views/PostStep3View.vue'
import PostStep4View from '../../user/views/PostStep4View.vue'
import AccountView from '../../user/views/AccountView.vue'
import FavoriteView from '../../user/views/FavoriteView.vue'
import MyListingView from '../../user/views/MyListingView.vue'
import MapView from '../../user/views/MapView.vue'
import ListingDetailView from '../../user/views/ListingDetailView.vue'
// ADMIN
import AdminLayout from '../../admin/views/AdminLayout.vue'
import DashboardView from '../../admin/views/DashboardView.vue'
import PostsView from '../../admin/views/PostsView.vue'
import UsersView from '../../admin/views/UsersView.vue'
import ReportsView from '../../admin/views/ReportsView.vue'
import AuditLogsView from '../../admin/views/AuditLogsView.vue'
import AiConfigView from '../../admin/views/AiConfigView.vue'

const routes = [
  // Khi mở web -> Login
  {
    path: '/',
    redirect: '/login'
  },

  // ================= USER =================

  {
    path: '/valuation',
    name: 'Valuation',
    component: () => import('../../user/views/ValuationView.vue')
  },

  {
    path: '/home',
    name: 'Home',
    component: HomeView
  },
  {
  path: '/listings',
  name: 'listings',
  component: () => import('../../user/views/ListingsView.vue'),
},
  {
  path: '/listing/:id',
  name: 'ListingDetail',
  component: ListingDetailView
},
{
  path: '/listing/:id/report',
  name: 'report-listing',
  component: () => import('../../user/views/ReportListingView.vue'),
},
  {
  path: '/map',
  name: 'Map',
  component: MapView
},

  {
  path: '/account',
  name: 'Account',
  component: AccountView
},
{
  path: '/account/reports',
  name: 'my-reports',
  component: () => import('../../user/views/MyReportsView.vue'),
},
{
  path: '/favorites',
  name: 'Favorites',
  component: FavoriteView
},

{
  path: '/my-listing',
  name: 'MyListing',
  component: MyListingView
},

  {
    path: '/post',
    name: 'Post',
    component: PostView
  },

   {
    path: '/post/step-2',
    name: 'PostStep2',
    component: PostStep2View
  },

  {
  path: '/post/step-3',
  name: 'PostStep3',
  component: PostStep3View
},

{
  path: '/post/step-4',
  name: 'PostStep4',
  component: PostStep4View
},

  {
    path: '/login',
    component: LoginView
  },

  {
    path: '/register',
    component: RegisterView
  },

  // ================= ADMIN =================

  {
    path: '/admin',
    component: AdminLayout,
    redirect: '/admin/dashboard',

    children: [
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: DashboardView
      },

      {
        path: 'posts',
        name: 'AdminPosts',
        component: PostsView
      },

      {
        path: 'users',
        name: 'AdminUsers',
        component: UsersView
      },

      {
        path: 'reports',
        name: 'AdminReports',
        component: ReportsView
      },

      {
        path: 'audit-logs',
        name: 'AdminAuditLogs',
        component: AuditLogsView
      },

      {
        path: 'ai-config',
        name: 'AdminAiConfig',
        component: AiConfigView
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
