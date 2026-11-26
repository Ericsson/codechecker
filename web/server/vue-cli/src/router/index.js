import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "products",
      alias: [ "/products.html" ],
      meta: {
        title: "Products",
        requiresAuth: true
      },
      component: () => import("@/views/Products")
    },
    {
      path: "/login",
      name: "login",
      alias: [ "/login.html" ],
      meta: { title: "Login" },
      component: () => import("@/views/Login")
    },
    {
      path: "/login/OAuthLogin/:provider",
      name: "oauthlogin",
      meta: { title: "Login" },
      component: () => import("@/views/OAuthLogin")
    },
    {
      path: "/userguide",
      name: "userguide",
      meta: { title: "User Guide" },
      component: () => import("@/views/Userguide"),
    },
    {
      path: "/new-features",
      name: "new-features",
      meta: { title: "New Features" },
      component: () => import("@/views/NewFeatures")
    },
    {
      path: "/404",
      name: "404",
      meta: { title: "Not Found" },
      component: () => import("@/views/NotFound")
    },
    {
      // Should be kept in sync with the regex from is_valid_product_endpoint
      // on the backend.
      path: "/:endpoint([A-Za-z0-9_-]+)?",
      meta: {
        requiresAuth: true
      },
      component: () => import("@/views/ProductDetail"),
      children: [
        {
          path: "",
          name: "main_runs",
          meta: { title: "Runs" },
          component: () => import("@/views/RunList")
        },
        {
          path: "runs",
          name: "runs",
          meta: { title: "Runs" },
          component: () => import("@/views/RunList")
        },
        {
          path: "statistics",
          name: "statistics",
          redirect: { name: "product-overview" },
          component: () => import("@/views/Statistics"),
          children: [
            {
              path: "overview",
              name: "product-overview",
              meta: { title: "Product Overview" },
              component: () =>
                import("@statistics/Overview/Overview"),
            },
            {
              path: "checker",
              name: "checker-statistics",
              meta: { title: "Checker Statistics" },
              component: () =>
                import("@statistics/Checker/CheckerStatistics"),
            },
            {
              path: "severity",
              name: "severity-statistics",
              meta: { title: "Severity Statistics" },
              component: () =>
                import("@statistics/Severity/SeverityStatistics"),
            },
            {
              path: "component",
              name: "component-statistics",
              meta: { title: "Component Statistics" },
              component: () => import(
                "@statistics/Component/ComponentStatistics"),
            },
            {
              path: "coverage",
              name: "checker-coverage-statistics",
              meta: { title: "Checker Coverage" },
              component: () =>
                import(
                  "@statistics/CheckerCoverage/CheckerCoverageStatistics"
                ),
            },
            {
              path: "guideline",
              name: "guideline-statistics",
              meta: { title: "Guideline Statistics" },
              component: () => import(
                "@/components/Statistics/Guideline/GuidelineStatistics"
              ),
            },
          ]
        },
        {
          path: "reports",
          name: "reports",
          meta: { title: "Reports" },
          component: () => import("@/views/Reports")
        },
        {
          path: "report-detail",
          name: "report-detail",
          component: () => import("@/views/ReportDetail")
        },
        {
          path: "cleanup-plan",
          name: "cleanup-plan",
          meta: { title: "Cleanup Plan" },
          component: () => import("@/views/CleanupPlan")
        },
        {
          path: "review-status-rules",
          name: "review-status-rules",
          meta: { title: "Review Status Rules" },
          component: () => import("@/views/ReviewStatusRules")
        },
        {
          path: "source-component",
          name: "source-component",
          meta: { title: "Source Component" },
          component: () => import("@/views/SourceComponent")
        },
      ]
    },
    {
      path: "/:unknown(.*)*",
      redirect: "/404"
    }
  ]
});

export default router;
