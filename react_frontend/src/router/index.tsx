/**
 * Application Router
 * Defines all routes and navigation structure
 */

import React, { Suspense, lazy } from 'react';
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Spinner } from '../components/ui';

// ============================================================================
// Lazy-loaded Pages
// ============================================================================

const LoginPage = lazy(() => import('../pages/LoginPage'));
const DashboardPage = lazy(() => import('../pages/DashboardPageEnhanced'));
const PatientDetailPage = lazy(() => import('../pages/PatientDetailPage'));
const QueryPage = lazy(() => import('../pages/QueryPageEnhanced'));
const ExplainabilityPage = lazy(() => import('../pages/ExplainabilityPage'));
const SystemStatusPage = lazy(() => import('../pages/SystemStatusPage'));
const SettingsPage = lazy(() => import('../pages/SettingsPage'));
const NotFoundPage = lazy(() => import('../pages/NotFoundPage'));

// ============================================================================
// Loading Fallback
// ============================================================================

const PageLoader: React.FC = () => (
  <div className="page-loader">
    <Spinner size="lg" />
    <p>Loading...</p>
  </div>
);

// ============================================================================
// Layout Components
// ============================================================================

/**
 * Main application layout with navigation
 */
const AppLayout: React.FC = () => {
  return (
    <div className="app-layout">
      <Navigation />
      <main className="app-layout__main">
        <Suspense fallback={<PageLoader />}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  );
};

/**
 * Navigation component
 */
const Navigation: React.FC = () => {
  const { userEmail, logout, isAuthenticated } = useAuth();

  return (
    <nav className="app-nav">
      <div className="app-nav__brand">
        <a href="/">AI Healthcare</a>
      </div>
      <div className="app-nav__links">
        <a href="/">Dashboard</a>
        <a href="/query">Medical Query</a>
        <a href="/system">System Status</a>
        <a href="/settings">Settings</a>
      </div>
      <div className="app-nav__user">
        {isAuthenticated && (
          <>
            <span>{userEmail}</span>
            <button onClick={logout}>Logout</button>
          </>
        )}
      </div>
    </nav>
  );
};

// ============================================================================
// Protected Route Wrapper
// ============================================================================

interface ProtectedRouteProps {
  children?: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <PageLoader />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children ?? <Outlet />}</>;
};

// ============================================================================
// Public Route Wrapper (redirects if already authenticated)
// ============================================================================

const PublicRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <PageLoader />;
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <>{children ?? <Outlet />}</>;
};

// ============================================================================
// Router Configuration
// ============================================================================

export const router = createBrowserRouter([
  // Public routes
  {
    path: '/login',
    element: (
      <PublicRoute>
        <Suspense fallback={<PageLoader />}>
          <LoginPage />
        </Suspense>
      </PublicRoute>
    ),
  },

  // Protected routes
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'patient/:id',
        element: <PatientDetailPage />,
      },
      {
        path: 'query',
        element: <QueryPage />,
      },
      {
        path: 'explain/:patientId',
        element: <ExplainabilityPage />,
      },
      {
        path: 'system',
        element: <SystemStatusPage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
    ],
  },

  // 404 catch-all
  {
    path: '*',
    element: (
      <Suspense fallback={<PageLoader />}>
        <NotFoundPage />
      </Suspense>
    ),
  },
]);

export default router;
