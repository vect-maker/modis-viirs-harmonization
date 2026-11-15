import { createMemoryHistory, createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import LandingView from "@/views/LandingView.vue";

const router = createRouter({
  history:
    typeof window !== "undefined"
      ? createWebHistory(import.meta.env.BASE_URL)
      : createMemoryHistory(),
  routes: [
    { path: "/", name: "landing", component: LandingView },
    {
      path: "/dashboard",
      name: "dashboard",
      component: () => import("@/views/ExplorerView.vue"),
    },
    {
      path: "/auth",
      redirect: { name: "login" },
      children: [
        {
          path: "login",
          name: "login",
          meta: { guestOnly: true },
          component: () => import("@/views/auth/LoginView.vue"),
        },
        {
          path: "register",
          name: "register",
          meta: { guestOnly: true },
          component: () => import("@/views/auth/RegisterView.vue"),
        },
      ],
    },
    {
      path: "/profile",
      name: "profile",
      meta: { requiresAuth: true },
      component: () => import("@/views/ProfileView.vue"),
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: { name: "landing" },
    },
  ],
  scrollBehavior(to) {
    if (to.hash) return { el: to.hash, behavior: "smooth" };
    return { top: 0 };
  },
});

router.beforeEach(async (to) => {
  const authStore = useAuthStore();
  await authStore.initSession();

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return {
      name: "login",
      query: { redirect: to.fullPath },
    };
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return { name: "dashboard" };
  }

  return true;
});

export default router;
