import Vue from "vue";
import Router from "vue-router";

Vue.use(Router);

export default new Router({
  routes: [
    {
      path: "/",
      name: "products",
      meta: {
        requiresAuth: true
      },
      component: () => import("@/views/Products")
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/Login")
    },
    {
      path: "/userguide",
      name: "userguide",
      component: () => import("@/views/Userguide")
    },
    {
      path: "/new-features",
      name: "new-features",
      component: () => import("@/views/NewFeatures")
    },
    {
      path: "/:endpoint",
      meta: {
        requiresAuth: true
      },
      component: () => import("@/views/ProductDetail"),
      children: [
        {
          path: "",
          component: () => import("@/views/RunList")
        },
        {
          path: "runs",
          name: "runs",
          component: () => import("@/views/RunList")
        },
        {
          path: "statistics",
          name: "statistics",
          component: () => import("@/views/Statistics")
        },
        {
          path: "run-history",
          name: "run-history",
          component: () => import("@/views/RunHistoryList")
        },
        {
          path: "reports",
          name: "reports",
          component: () => import("@/views/Reports")
        },
        {
          path: "report-detail",
          name: "report-detail",
          component: () => import("@/views/ReportDetail")
        }
      ]
    }
  ]
});