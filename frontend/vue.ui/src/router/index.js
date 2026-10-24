import {createRouter,createWebHistory} from 'vue-router'
import {session,loadProfile,restoreSession,refreshEnabled} from '../services/api'
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
 AiConfigView:()=>import('../../admin/views/AiConfigView.vue')
}
const routes=[
 {path:'/',redirect:'/home'},
 ...Object.entries({home:'HomeView',listings:'ListingsView',map:'MapView',favorites:'FavoriteView','my-listing':'MyListingView'}).map(([path,view])=>({path:'/'+path,component:restoredViews[view]})),
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
 {path:'/account/reports',component:()=>import('../../user/views/MyReportsView.vue')},
 ...['/post','/post/step-2','/post/step-3'].map(path=>({path,component:restoredViews.PostView})),
 {path:'/post/step-4',redirect:to=>({path:'/post/step-3',query:to.query,hash:to.hash})},
 {path:'/login',component:()=>import('../components/LoginView.vue')},
 {path:'/register',component:()=>import('../components/RegisterView.vue')},
 {path:'/admin',component:()=>import('../../admin/views/AdminLayout.vue'),redirect:'/admin/dashboard',children:Object.entries({dashboard:'DashboardView',posts:'PostsView',users:'UsersView',reports:'ReportsView','audit-logs':'AuditLogsView','ai-config':'AiConfigView',projects:'ProjectsView'}).map(([path,view])=>({path,component:restoredViews[view]}))},
 {path:'/:pathMatch(.*)*',redirect:'/home'},
]
const router=createRouter({history:createWebHistory(),routes,scrollBehavior:(to,from,savedPosition)=>savedPosition||(['/home','/listings'].includes(to.path)&&to.path===from.path?false:to.path.startsWith('/post')&&to.hash?{el:to.hash,top:100,behavior:'smooth'}:{top:0})})
router.beforeEach(async to=>{
 const admin=to.path.startsWith('/admin'),publisher=to.path==='/post'||to.path.startsWith('/post/')
 const protectedRoute=admin||publisher||['/account','/favorites','/my-listing'].some(path=>to.path===path||to.path.startsWith(path+'/'))||to.path.endsWith('/report')||to.query.own==='1'
 if(!protectedRoute)return true
 if(!session.token&&refreshEnabled)await restoreSession()
 if(!session.token)return {path:'/login',query:{reason:'login-required'}}
 try{await loadProfile()}catch{return {path:'/login',query:{reason:'session-unavailable'}}}
 if(admin&&session.user.role!=='ADMIN')return '/home'
 if(publisher&&!['ADMIN','BROKER'].includes(session.user.role))return '/my-listing'
 return true
})
window.addEventListener('smartprop:session-expired',()=>router.replace({path:'/login',query:{reason:'session-expired'}}))
export default router