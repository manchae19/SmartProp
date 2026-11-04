import {createRouter,createWebHistory} from 'vue-router'
import {session,loadProfile,initializeAuth,authUnavailable} from '../features/auth/api.js'
import {homeSectionId,navigationOffset} from '../lib/siteNavigation.js'
import SessionRecovery from '../features/auth/SessionRecovery.vue'
const restoredViews={
 HomeView:()=>import('../features/home/HomeView.vue'),
 ListingsView:()=>import('../features/property/ListingsView.vue'),
 MapView:()=>import('../features/map/MapView.vue'),
 FavoriteView:()=>import('../features/favorite/FavoriteView.vue'),
 MyListingView:()=>import('../features/property/MyListingView.vue'),
 PostView:()=>import('../features/property/PostView.vue'),
 DashboardView:()=>import('../features/admin/DashboardView.vue'),
 PostsView:()=>import('../features/admin/PostsView.vue'),
 UsersView:()=>import('../features/admin/UsersView.vue'),
 ReportsView:()=>import('../features/admin/ReportsView.vue'),
 AuditLogsView:()=>import('../features/admin/AuditLogsView.vue'),
 ProjectsView:()=>import('../features/admin/ProjectsView.vue'),
 BrokerApplicationsView:()=>import('../features/admin/BrokerApplicationsView.vue'),
 AiConfigView:()=>import('../features/admin/AiConfigView.vue')
}
const routes=[
 {path:'/',redirect:'/home'},
 ...Object.entries({home:'HomeView',listings:'ListingsView',map:'MapView',favorites:'FavoriteView','my-listing':'MyListingView'}).map(([path,view])=>({path:'/'+path,component:restoredViews[view]})),
 {path:'/auth/google/complete',component:()=>import('../features/auth/GoogleCompleteView.vue')},
 {path:'/valuation',component:()=>import('../features/prediction/ValuationView.vue')},
 {path:'/market',component:()=>import('../features/market/MarketInsightsView.vue')},
 {path:'/market/:district',component:()=>import('../features/market/MarketInsightsView.vue')},
 {path:'/market-insights',redirect:'/market'},
 {path:'/market-insights/:district',redirect:to=>({path:'/market/'+to.params.district})},
 {path:'/advisor',component:()=>import('../features/prediction/AdvisorView.vue')},
 {path:'/advisor/chat',component:()=>import('../features/prediction/ChatAdvisorView.vue')},
 {path:'/projects',component:()=>import('../features/project/ProjectsView.vue')},
 {path:'/projects/:id',component:()=>import('../features/project/ProjectDetailView.vue')},
 {path:'/listing/:id',component:()=>import('../features/property/ListingDetailView.vue')},
 {path:'/listing/:id/report',component:()=>import('../features/report/ReportListingView.vue')},
 {path:'/account/properties/:id/legal-documents',component:()=>import('../features/legal/LegalDocumentsView.vue')},
 {path:'/account/sessions',component:()=>import('../features/account/SessionsView.vue')},
 {path:'/account/notifications',component:()=>import('../features/notification/NotificationsView.vue')},
 {path:'/account/messages',component:()=>import('../features/messaging/MessagesView.vue')},
 {path:'/account/verify-email',component:()=>import('../features/auth/EmailActionView.vue')},
 {path:'/reset-password',component:()=>import('../features/auth/EmailActionView.vue')},
 {path:'/verify-email',component:()=>import('../features/auth/EmailActionView.vue')},
 {path:'/account',component:()=>import('../features/account/AccountView.vue')},
 {path:'/account/broker-application',component:()=>import('../features/broker/BrokerApplicationView.vue')},
 {path:'/account/reports',component:()=>import('../features/report/MyReportsView.vue')},
 ...['/post','/post/step-2','/post/step-3'].map(path=>({path,component:restoredViews.PostView})),
 {path:'/post/step-4',redirect:to=>({path:'/post/step-3',query:to.query,hash:to.hash})},
 {path:'/session-recovery',component:SessionRecovery},
 {path:'/login',component:()=>import('../features/auth/LoginView.vue')},
 {path:'/register',component:()=>import('../features/auth/RegisterView.vue')},
 {path:'/admin',component:()=>import('../features/admin/AdminLayout.vue'),redirect:'/admin/dashboard',children:Object.entries({dashboard:'DashboardView',posts:'PostsView',users:'UsersView',reports:'ReportsView','audit-logs':'AuditLogsView','ai-config':'AiConfigView',projects:'ProjectsView','broker-applications':'BrokerApplicationsView'}).map(([path,view])=>({path,component:restoredViews[view]}))},
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
