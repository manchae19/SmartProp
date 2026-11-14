import App from './App.jsx'
import {createAppRouter} from '../shared/routing/router.jsx'
import {session,loadProfile,initializeAuth,authUnavailable} from '../features/auth/api.js'
import {homeSectionId,navigationOffset} from '../shared/lib/siteNavigation.js'
import SessionRecovery from '../features/auth/SessionRecovery.jsx'
const restoredViews={
 HomeView:()=>import('../features/home/HomeView.jsx'),
 ListingsView:()=>import('../features/property/ListingsView.jsx'),
 MapView:()=>import('../features/map/MapView.jsx'),
 FavoriteView:()=>import('../features/favorite/FavoriteView.jsx'),
 MyListingView:()=>import('../features/property/MyListingView.jsx'),
 PostView:()=>import('../features/property/PostView.jsx'),
 DashboardView:()=>import('../features/admin/DashboardView.jsx'),
 PostsView:()=>import('../features/admin/PostsView.jsx'),
 UsersView:()=>import('../features/admin/UsersView.jsx'),
 ReportsView:()=>import('../features/admin/ReportsView.jsx'),
 AuditLogsView:()=>import('../features/admin/AuditLogsView.jsx'),
 ProjectsView:()=>import('../features/admin/ProjectsView.jsx'),
 BrokerApplicationsView:()=>import('../features/admin/BrokerApplicationsView.jsx'),
 AiConfigView:()=>import('../features/admin/AiConfigView.jsx')
}
const routes=[
 {path:'/',redirect:'/home'},
 ...Object.entries({home:'HomeView',listings:'ListingsView',map:'MapView',favorites:'FavoriteView','my-listing':'MyListingView'}).map(([path,view])=>({path:'/'+path,component:restoredViews[view]})),
 {path:'/auth/google/complete',component:()=>import('../features/auth/GoogleCompleteView.jsx')},
 {path:'/valuation',component:()=>import('../features/prediction/ValuationView.jsx')},
 {path:'/market',redirect:'/market-analytics'},
 {path:'/market/:district',redirect:'/market-analytics'},
 {path:'/market-insights',redirect:'/market-analytics'},
 {path:'/market-insights/:district',redirect:'/market-analytics'},
 // Real-data market analytics (Step 21.5B) — legacy demo routes above now redirect here.
 {path:'/market-analytics',component:()=>import('../features/market/MarketAnalyticsView.jsx')},
 // Comparable listings lookup (BROKER/ADMIN) — additive.
 {path:'/comparables',component:()=>import('../features/property/ComparablesView.jsx')},
 {path:'/advisor',component:()=>import('../features/prediction/AdvisorView.jsx')},
 {path:'/advisor/chat',component:()=>import('../features/prediction/ChatAdvisorView.jsx')},
 // Unified AI Advisor (ADVISOR_ORCHESTRATOR_V1) — distinct from the RAG chat above.
 {path:'/advisor/analysis',component:()=>import('../features/prediction/UnifiedAdvisorView.jsx')},
 {path:'/image-check',component:()=>import('../features/imagecheck/ImageCheckView.jsx')},
 {path:'/image-analysis',component:()=>import('../features/imageanalysis/ImageAnalysisView.jsx')},
 {path:'/projects',component:()=>import('../features/project/ProjectsView.jsx')},
 {path:'/projects/:id',component:()=>import('../features/project/ProjectDetailView.jsx')},
 {path:'/listing/:id',component:()=>import('../features/property/ListingDetailView.jsx')},
 {path:'/listing/:id/report',component:()=>import('../features/report/ReportListingView.jsx')},
 {path:'/account/properties/:id/legal-documents',component:()=>import('../features/legal/LegalDocumentsView.jsx')},
 {path:'/account/sessions',component:()=>import('../features/account/SessionsView.jsx')},
 {path:'/account/notifications',component:()=>import('../features/notification/NotificationsView.jsx')},
 {path:'/account/messages',component:()=>import('../features/messaging/MessagesView.jsx')},
 {path:'/account/verify-email',component:()=>import('../features/auth/EmailActionView.jsx')},
 {path:'/reset-password',component:()=>import('../features/auth/EmailActionView.jsx')},
 {path:'/verify-email',component:()=>import('../features/auth/EmailActionView.jsx')},
 {path:'/account',component:()=>import('../features/account/AccountView.jsx')},
 {path:'/account/broker-application',component:()=>import('../features/broker/BrokerApplicationView.jsx')},
 {path:'/account/reports',component:()=>import('../features/report/MyReportsView.jsx')},
 ...['/post','/post/step-2','/post/step-3'].map(path=>({path,component:restoredViews.PostView})),
 {path:'/post/step-4',redirect:to=>({path:'/post/step-3',query:to.query,hash:to.hash})},
 {path:'/session-recovery',component:SessionRecovery},
 {path:'/login',component:()=>import('../features/auth/LoginView.jsx')},
 {path:'/register',component:()=>import('../features/auth/RegisterView.jsx')},
 {path:'/admin',component:()=>import('../features/admin/AdminLayout.jsx'),redirect:'/admin/dashboard',children:Object.entries({dashboard:'DashboardView',posts:'PostsView',users:'UsersView',reports:'ReportsView','audit-logs':'AuditLogsView','ai-config':'AiConfigView',projects:'ProjectsView','broker-applications':'BrokerApplicationsView'}).map(([path,view])=>({path,component:restoredViews[view]}))},
 {path:'/:pathMatch(.*)*',redirect:'/home'},
]
const router=createAppRouter({root:App,routes,scrollBehavior(to,from,savedPosition){
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
