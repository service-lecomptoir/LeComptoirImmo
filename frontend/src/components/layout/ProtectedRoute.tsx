import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import type { Role } from '@/types/auth'

interface ProtectedRouteProps {
  requiredRole?: Role
}

const ROLE_HIERARCHY: Record<Role, number> = {
  lecture: 1,
  comptable: 2,
  gestionnaire: 3,
  admin: 4,
}

export function ProtectedRoute({ requiredRole }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requiredRole) {
    const userLevel = ROLE_HIERARCHY[user.role] ?? 0
    const requiredLevel = ROLE_HIERARCHY[requiredRole] ?? 0
    if (userLevel < requiredLevel) {
      return <Navigate to="/unauthorized" replace />
    }
  }

  return <Outlet />
}
