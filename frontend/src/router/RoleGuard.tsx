import { Navigate } from "react-router-dom";

import { useAuthStore } from "../store/auth.store";
import type { UserRole } from "../types/auth";

type RoleGuardProps = {
  children: React.ReactNode;
  allow?: UserRole[];
};

export default function RoleGuard({ children, allow }: RoleGuardProps) {
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const isHydrated = useAuthStore((state) => state.isHydrated);

  if (!isHydrated) {
    return <div className="screen-center">Loading session...</div>;
  }

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  if (allow && !allow.includes(user.role)) {
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
}
