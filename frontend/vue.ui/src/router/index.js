import {createRouter,createWebHistory} from 'vue-router'
import {session,loadProfile,initializeAuth,authUnavailable} from '../services/api'
import {homeSectionId,navigationOffset} from '../services/siteNavigation.js'
import SessionRecovery from '../components/SessionRecovery.vue'
const restoredViews={
 HomeView:()=>import('../../user/views/HomeView.vue'),
 ListingsView:()=>import('../../user/views/ListingsView.vue'),
 MapView:()=>import('../../user/views/MapView.vue'),
 FavoriteView:()=>import('../../user/views/FavoriteView.vue'),
 MyListingView:()=>import('../../user/views/MyListingView.vue'),
 PostView:()=>import('../../user/views/PostView.vue'),
 DashboardView:()=>import('../../admin/views/DashboardView.vue'),
 PostsView:()=>import('../../admin/views/PostsView.vue'),
 UsersView:()=>import('../../admin/views/UsersView.vue'),
 ReportsView:()=>import('../../admin/views/ReportsView.vue'),
 AuditLogsView:()=>import('../../admin/views/AuditLogsView.vue'),
 ProjectsView:()=>import('../../admin/views/ProjectsView.vue'),
 BrokerApplicationsView:()=>import('../../admin/views/BrokerApplicationsView.vue'),
 AiConfigView:()=>import('../../admin/views/AiConfigView.vue')
}
const routes=[
 {path:'/',redirect:'/home'},
 ...Object.entries({home:'HomeView',listings:'ListingsView',map:'MapView',favorites:'FavoriteView','my-listing':'MyListingView'}).map(([path,view])=>({path:'/'+path,component:restoredViews[view]})),
 {path:'/projects',component:()=>import('../../user/views/ProjectsView.vue')},
 {path:'/projects/:id',component:()=>import('../../user/views/ProjectDetailView.vue')},
 {path:'/listing/:id',component:()=>import('../../user/views/ListingDetailView.vue')},
 {path:'/listing/:id/report',component:()=>import('../../user/views/ReportListingView.vue')},
 {path:'/account/properties/:id/legal-documents',component:()=>import('../../user/views/LegalDocumentsView.vue')},
 {path:'/account/sessions',component:()=>import('../../user/views/SessionsView.vue')},
 {path:'/account/notifications',component:()=>import('../../user/views/NotificationsView.vue')},
 {path:'/account/messages',component:()=>import('../../user/views/MessagesView.vue')},
 {path:'/account/verify-email',component:()=>import('../../user/views/EmailActionView.vue')},
 {path:'/reset-password',component:()=>import('../../user/views/EmailActionView.vue')},
 {path:'/verify-email',component:()=>import('../../user/views/EmailActionView.vue')},
 {path:'/account',component:()=>import('../../user/views/AccountView.vue')},
 {path:'/account/broker-application',component:()=>import('../../user/views/BrokerApplicationView.vue')},
 {path:'/account/reports',component:()=>import('../../user/views/MyReportsView.vue')},
 ...['/post','/post/step-2','/post/step-3'].map(path=>({path,component:restoredViews.PostView})),
 {path:'/post/step-4',redirect:to=>({path:'/post/step-3',query:to.query,hash:to.hash})},
 {path:'/session-recovery',component:SessionRecovery},
 {path:'/login',component:()=>import('../components/LoginView.vue')},
 {path:'/register',component:()=>import('../components/RegisterView.vue')},
 {path:'/admin',component:()=>import('../../admin/views/AdminLayout.vue'),redirect:'/admin/dashboard',children:Object.entries({dashboard:'DashboardView',posts:'PostsView',users:'UsersView',reports:'ReportsView','audit-logs':'AuditLogsView','ai-config':'AiConfigView',projects:'ProjectsView','broker-applications':'BrokerApplicationsView'}).map(([path,view])=>({path,component:restoredViews[view]}))},
 {path:'/:pathMatch(.*)*',redirect:'/home'},
]
const router=createRouter({history:createWebHistory(),routes,scrollBehavior(to,from,savedPosition){
 if(savedPosition)return savedPosition
 if(['/home','/listings','/map'].includes(to.path)&&to.path===from.path&&to.hash===from.hash)return false
 if(to.path==='/home'&&to.hash){
  const target=homeSectionId(to.hash)
  if(target)return {el:'#'+target,top:navigationOffset(),behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'}
 }
 return to.path.startsWith('/post')&&to.hash?{el:to.hash,top:100,behavior:'smooth'}:{top:0}
}})
router.beforeEach(async to=>{
 await initializeAuth()
 const admin=to.path.startsWith('/admin'),publisher=to.path==='/post'||to.path.startsWith('/post/')
 const protectedRoute=admin||publisher||['/account','/favorites','/my-listing'].some(path=>to.path===path||to.path.startsWith(path+'/'))||to.path.endsWith('/report')||to.query.own==='1'
 if(!protectedRoute)return true
 if(session.status==='UNAVAILABLE')return {path:'/session-recovery',query:{returnTo:to.fullPath}}
 if(!session.token)return {path:'/login',query:{reason:'login-required'}}
 try{await loadProfile()}catch(error){if(error.status===401)return {path:'/login',query:{reason:'session-unavailable'}};authUnavailable(error);return {path:'/session-recovery',query:{returnTo:to.fullPath}}}
 if(admin&&session.user.role!=='ADMIN')return '/home'
 if(to.path==='/account/broker-application'&&session.user.role==='ADMIN')return '/admin/broker-applications'
 if(to.path==='/account/broker-application'&&session.user.role==='BROKER')return '/account'
 if(publisher&&(session.user.status!=='ACTIVE'||!['ADMIN','BROKER'].includes(session.user.role)))return '/account/broker-application'
 return true
})
window.addEventListener('smartprop:session-expired',()=>router.replace({path:'/login',query:{reason:'session-expired'}}))
export default router
