import { Navigate } from "react-router-dom";

import { useAuthStore } from "../store/auth.store";
import { resolveUserHomePath } from "../types/auth";

type PublicRouteProps = {
  children: React.ReactNode;
};

export default function PublicRoute({ children }: PublicRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isHydrated = useAuthStore((state) => state.isHydrated);

  if (!isHydrated) {
    return <div className="screen-center">Loading session...</div>;
  }

  if (isAuthenticated) {
    const user = useAuthStore.getState().user;
    return <Navigate to={user ? resolveUserHomePath(user.role) : "/dashboard"} replace />;
  }

  return <>{children}</>;
}
