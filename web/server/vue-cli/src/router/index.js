import Vue from 'vue';
import Router from 'vue-router';

Vue.use(Router);

export default new Router({
  routes: [
    {
      path: '/',
      name: 'products',
      component: () => import('@/views/Products')
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login')
    },
    {
      path: '/permission',
      name: 'global-permission',
      component: () => import('@/views/Permission')
    },
    {
      path: '/p/new',
      name: 'product-new',
      component: () => import('@/views/ProductNew')
    },
    {
      path: '/p/edit/:endpoint',
      name: 'product-edit',
      component: () => import('@/views/ProductEdit')
    },
    {
      path: '/p/permissions/:endpoint',
      name: 'product-permission',
      component: () => import('@/views/ProductPermission')
    },
    {
      path: '/:endpoint',
      component: () => import('@/views/ProductDetail'),
      children: [
        {
          path: '',
          component: () => import('@/views/RunList')
        },
        {
          path: 'runs',
          name: 'runs',
          component: () => import('@/views/RunList')
        },
        {
          path: 'statistics',
          name: 'statistics',
          component: () => import('@/views/Statistics')
        },
        {
          path: 'reports',
          name: 'reports',
          component: () => import('@/views/Reports')
        },
        {
          path: 'reports/:name',
          name: 'report-detail',
          component: () => import('@/views/ReportDetail')
        }
      ]
    }
  ]
});