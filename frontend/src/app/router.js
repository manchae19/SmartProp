import React, { Suspense } from 'react';
import { createBrowserRouter, redirect } from 'react-router-dom';
import App from './App.jsx';
import { session, loadProfile, initializeAuth, authUnavailable } from '../features/auth/api.js';
import SessionRecovery from '../features/auth/SessionRecovery.jsx';
import { toUrl, queryFromSearch } from './navigation.jsx';
const restoredViews = {
  HomeView: () => import('../features/home/HomeView.jsx'),
  ListingsView: () => import('../features/property/ListingsView.jsx'),
  MapView: () => import('../features/map/MapView.jsx'),
  FavoriteView: () => import('../features/favorite/FavoriteView.jsx'),
  MyListingView: () => import('../features/property/MyListingView.jsx'),
  PostView: () => import('../features/property/PostView.jsx'),
  DashboardView: () => import('../features/admin/DashboardView.jsx'),
  PostsView: () => import('../features/admin/PostsView.jsx'),
  UsersView: () => import('../features/admin/UsersView.jsx'),
  ReportsView: () => import('../features/admin/ReportsView.jsx'),
  AuditLogsView: () => import('../features/admin/AuditLogsView.jsx'),
  ProjectsView: () => import('../features/admin/ProjectsView.jsx'),
  BrokerApplicationsView: () => import('../features/admin/BrokerApplicationsView.jsx'),
  AiConfigView: () => import('../features/admin/AiConfigView.jsx'),
  CoordinateReviewView: () => import('../features/admin/AdminCoordinateReviewView.jsx')
};
const routes = [
  {path:'/market-analytics', component:()=>import('../features/market/MarketAnalyticsView.jsx')},
  {path:'/comparables', component:()=>import('../features/property/ComparablesView.jsx'), meta:{requiresAuth:true,roles:['BROKER','ADMIN']}},
  {path:'/advisor/analysis', component:()=>import('../features/prediction/UnifiedAdvisorView.jsx')},
  {path:'/image-check', component:()=>import('../features/imagecheck/ImageCheckView.jsx')},
  {path:'/image-analysis', component:()=>import('../features/imageanalysis/ImageAnalysisView.jsx')},
{
  path: '/',
  redirect: '/home'
}, ...Object.entries({
  home: 'HomeView',
  listings: 'ListingsView',
  map: 'MapView',
  favorites: 'FavoriteView',
  'my-listing': 'MyListingView'
}).map(([path, view]) => ({
  path: '/' + path,
  component: restoredViews[view]
})), {
  path: '/auth/google/complete',
  component: () => import('../features/auth/GoogleCompleteView.jsx')
}, {
  path: '/auth/google/link/complete',
  component: () => import('../features/auth/GoogleLinkCompleteView.jsx')
}, {
  path: '/valuation',
  component: () => import('../features/prediction/ValuationView.jsx')
}, {
  path: '/market',
  component: () => import('../features/market/MarketInsightsView.jsx')
}, {
  path: '/market/:district',
  component: () => import('../features/market/MarketInsightsView.jsx')
}, {
  path: '/market-insights',
  redirect: '/market'
}, {
  path: '/market-insights/:district',
  redirect: to => ({
    path: '/market/' + to.params.district
  })
}, {
  path: '/advisor',
  component: () => import('../features/prediction/AdvisorView.jsx')
}, {
  path: '/advisor/chat',
  component: () => import('../features/prediction/ChatAdvisorView.jsx')
}, {
  path: '/projects',
  component: () => import('../features/project/ProjectsView.jsx')
}, {
  path: '/projects/:id',
  component: () => import('../features/project/ProjectDetailView.jsx')
}, {
  path: '/listing/:id',
  component: () => import('../features/property/ListingDetailView.jsx')
}, {
  path: '/listing/:id/report',
  component: () => import('../features/report/ReportListingView.jsx')
}, {
  path: '/account/properties/:id/legal-documents',
  component: () => import('../features/legal/LegalDocumentsView.jsx')
}, {
  path: '/account/sessions',
  component: () => import('../features/account/SessionsView.jsx')
}, {
  path: '/account/notifications',
  component: () => import('../features/notification/NotificationsView.jsx')
}, {
  path: '/account/messages',
  component: () => import('../features/messaging/MessagesView.jsx')
}, {
  path: '/account/verify-email',
  component: () => import('../features/auth/EmailActionView.jsx')
}, {
  path: '/reset-password',
  component: () => import('../features/auth/EmailActionView.jsx')
}, {
  path: '/verify-email',
  component: () => import('../features/auth/EmailActionView.jsx')
}, {
  path: '/account',
  component: () => import('../features/account/AccountView.jsx')
}, {
  path: '/account/broker-application',
  component: () => import('../features/broker/BrokerApplicationView.jsx')
}, {
  path: '/account/reports',
  component: () => import('../features/report/MyReportsView.jsx')
}, ...['/post', '/post/step-2', '/post/step-3'].map(path => ({
  path,
  component: restoredViews.PostView
})), {
  path: '/post/step-4',
  redirect: to => ({
    path: '/post/step-3',
    query: to.query,
    hash: to.hash
  })
}, {
  path: '/session-recovery',
  component: SessionRecovery
}, {
  path: '/login',
  component: () => import('../features/auth/LoginView.jsx')
}, {
  path: '/register',
  component: () => import('../features/auth/RegisterView.jsx')
}, {
  path: '/admin',
  component: () => import('../features/admin/AdminLayout.jsx'),
  redirect: '/admin/dashboard',
  children: Object.entries({
    dashboard: 'DashboardView',
    posts: 'PostsView',
    users: 'UsersView',
    reports: 'ReportsView',
    'audit-logs': 'AuditLogsView',
    'ai-config': 'AiConfigView',
    projects: 'ProjectsView',
    'broker-applications': 'BrokerApplicationsView',
    'coordinate-review': 'CoordinateReviewView'
  }).map(([path, view]) => ({
    path,
    component: restoredViews[view]
  }))
}, {
  path: '/:pathMatch(.*)*',
  redirect: '/home'
}];
async function authorize(to) {
  await initializeAuth();
  const admin = to.path.startsWith('/admin'),
    publisher = to.path === '/post' || to.path.startsWith('/post/');
  const protectedRoute = admin || publisher || ['/account', '/favorites', '/my-listing'].some(path => to.path === path || to.path.startsWith(path + '/')) || to.path.endsWith('/report') || to.query.own === '1';
  if (!protectedRoute) return true;
  if (session.getSnapshot().status === 'UNAVAILABLE') return {
    path: '/session-recovery',
    query: {
      returnTo: to.fullPath
    }
  };
  if (!session.getSnapshot().token) return {
    path: '/login',
    query: {
      reason: 'login-required'
    }
  };
  try {
    await loadProfile();
  } catch (error) {
    if (error.status === 401) return {
      path: '/login',
      query: {
        reason: 'session-unavailable'
      }
    };
    authUnavailable(error);
    return {
      path: '/session-recovery',
      query: {
        returnTo: to.fullPath
      }
    };
  }
  if (admin && session.getSnapshot().user.role !== 'ADMIN') return '/home';
  if (to.path === '/account/broker-application' && session.getSnapshot().user.role === 'ADMIN') return '/admin/broker-applications';
  if (to.path === '/account/broker-application' && session.getSnapshot().user.role === 'BROKER') return '/account';
  if (publisher && (session.getSnapshot().user.status !== 'ACTIVE' || !['ADMIN', 'BROKER'].includes(session.getSnapshot().user.role))) return '/account/broker-application';
  return true;
}
const Loading = () => React.createElement('div', {
  role: 'status',
  className: 'grid min-h-screen place-items-center bg-brand-cream text-brand-navy'
}, 'SmartProp...');
function RouteError() {
  return React.createElement('div', {
    role: 'alert',
    className: 'p-8 text-brand-navy'
  }, React.createElement('p', null, 'Không tải được trang. Vui lòng thử lại.'), React.createElement('button', {
    type: 'button',
    onClick: () => location.reload()
  }, 'Tải lại'));
}
function convert(route) {
  let element;
  if (route.component) {
    const Component = route.component === SessionRecovery ? SessionRecovery : React.lazy(route.component);
    element = React.createElement(Suspense, {
      fallback: React.createElement(Loading)
    }, React.createElement(Component, route.props || {}));
  }
  return {
    path: route.path === '/:pathMatch(.*)*' ? '*' : route.path,
    element,
    children: route.children?.map(convert),
    loader: async ({
      request,
      params
    }) => {
      const url = new URL(request.url),
        to = {
          path: url.pathname,
          fullPath: url.pathname + url.search + url.hash,
          query: queryFromSearch(url.search),
          hash: url.hash,
          params
        };
      const decision = await authorize(to);
      if (decision && decision !== true) throw redirect(toUrl(decision));
      if (route.redirect && (!route.children || to.path === route.path)) {
        const target = typeof route.redirect === 'function' ? route.redirect(to) : route.redirect;
        throw redirect(toUrl(target));
      }
      return null;
    }
  };
}
const router = createBrowserRouter([{
  element: React.createElement(App),
  errorElement: React.createElement(RouteError),
  HydrateFallback: Loading,
  children: routes.map(convert)
}]);
window.addEventListener('smartprop:session-expired', () => router.navigate('/login?reason=session-expired', {
  replace: true
}));
export default router;
