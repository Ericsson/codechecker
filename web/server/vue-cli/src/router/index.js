import Vue from 'vue';
import Router from 'vue-router';

Vue.use(Router);

export default new Router({
  routes: [
    {
      path: '/',
      name: 'products',
      meta: {
        requiresAuth: true
      },
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
      meta: {
        requiresAuth: true
      },
      component: () => import('@/views/Permission')
    },
    {
      path: '/p/new',
      name: 'product-new',
      meta: {
        requiresAuth: true
      },
      component: () => import('@/views/ProductNew')
    },
    {
      path: '/p/edit/:endpoint',
      name: 'product-edit',
      meta: {
        requiresAuth: true
      },
      component: () => import('@/views/ProductEdit')
    },
    {
      path: '/p/permissions/:endpoint',
      name: 'product-permission',
      meta: {
        requiresAuth: true
      },
      component: () => import('@/views/ProductPermission')
    },
    {
      path: '/:endpoint',
      meta: {
        requiresAuth: true
      },
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
          path: ':run',
          component: () => import('@/views/RunDetail'),
          children: [
            {
              path: '',
              name: 'reports',
              component: () => import('@/views/Reports')
            },
            {
              path: ':name',
              name: 'report-detail',
              component: () => import('@/views/ReportDetail')
            }
          ]
        }
      ]
    }
  ]
});