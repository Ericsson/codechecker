import Vue from "vue";
import Router from "vue-router";

Vue.use(Router);

export default new Router({
  mode: "history",
  routes: [
    {
      path: "/",
      name: "products",
      alias: [ "/products.html" ],
      meta: {
        requiresAuth: true
      },
      component: () => import("@/views/Products")
    },
    {
      path: "/login",
      name: "login",
      alias: [ "/login.html" ],
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
      path: "/404",
      name: "404",
      component: () => import("@/views/NotFound")
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
          name: "main_runs",
          component: () => import("@/views/RunList")
        },
        {
          path: "runs",
          name: "runs",
          component: () => import("@/views/RunList")
        },
        {
          path: "statistics",
          component: () => import("@/views/Statistics"),
          children: [
            {
              path: "",
              name: "statistics",
              redirect: "overview"
            },
            {
              path: "overview",
              name: "product-overview",
              component: () =>
                import("@/components/Statistics/Overview/Overview"),
            },
            {
              path: "checker",
              name: "checker-statistics",
              component: () =>
                import("@/components/Statistics/Checker/CheckerStatistics"),
            },
            {
              path: "severity",
              name: "severity-statistics",
              component: () =>
                import("@/components/Statistics/Severity/SeverityStatistics"),
            },
            {
              path: "component",
              name: "component-statistics",
              component: () => import(
                "@/components/Statistics/Component/ComponentStatistics"),
            }
          ]
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