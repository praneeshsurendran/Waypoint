import { lazy, Suspense } from 'react'
import { appRoutes, appModules, roleModules } from '@/app/router/registry'

import { ErrorBoundary } from '@/app/providers/ErrorBoundary'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { RouteMetadataContext } from '@/app/providers/RouteMetadataContext'
import { DriverRuntimeBoundary } from '@/app/providers/DriverRuntime'

import { SignInGuard } from '@/app/router/guards/SignInGuard'

import { RoleRouteGuard } from '@/app/router/guards/RoleRouteGuard'
const WorkspaceLayout = lazy(() => import('@/components/templates/WorkspaceLayout'))
const NotFoundView = lazy(() =>
  import('@/app/recovery/NotFoundPage').then((module) => ({ default: module.NotFoundView })),
)

const DemoMapPage = lazy(() => import('@/app/demo/DemoMapPage'))

const DemoPage = lazy(() => import('@/app/demo/DemoPage'))

const realBackend = !!import.meta.env.VITE_API_URL && import.meta.env.VITE_API_URL !== ''

const standaloneRoutes = appRoutes.filter((route) => !route.shell)

const sharedShellRoutes = appModules
  .filter((mod) => !roleModules.some((rm) => rm.key === mod.key))
  .flatMap((mod) => mod.routes.filter((route) => route.shell))

export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <RouteMetadataContext.Provider value={appRoutes}>
          <DriverRuntimeBoundary>
            <Suspense
              fallback={
                <div className="min-h-[70dvh] grid place-items-center text-muted-foreground">
                  Opening your workspace…
                </div>
              }
            >
              <Routes>
                {realBackend ? (
                  <Route path="/demo/*" element={<Navigate to="/welcome" replace />} />
                ) : (
                  <>
                    <Route path="/demo/map" element={<DemoMapPage />} />
                    <Route path="/demo" element={<DemoPage />} />
                  </>
                )}
                <Route path="/" element={<Navigate to="/welcome" replace />} />
                <Route path="/index.html" element={<Navigate to="/welcome" replace />} />
                {standaloneRoutes.map(({ path, component: Page }) => (
                  <Route
                    key={path}
                    path={path}
                    element={
                      path === '/workspaces' ? (
                        <SignInGuard>
                          <Page />
                        </SignInGuard>
                      ) : (
                        <Page />
                      )
                    }
                  />
                ))}
                <Route
                  element={
                    <WorkspaceLayout>
                      <Outlet />
                    </WorkspaceLayout>
                  }
                >
                  {roleModules.map((module) =>
                    module.routes
                      .filter((route) => route.shell)
                      .map(({ path, component: Page }) => (
                        <Route
                          key={path}
                          path={path}
                          element={
                            <RoleRouteGuard allowedRole={module.key}>
                              <Page />
                            </RoleRouteGuard>
                          }
                        />
                      )),
                  )}
                  {sharedShellRoutes.map(({ path, component: Page }) => (
                    <Route
                      key={path}
                      path={path}
                      element={
                        <SignInGuard>
                          <Page />
                        </SignInGuard>
                      }
                    />
                  ))}
                  <Route path="*" element={<NotFoundView />} />
                </Route>
              </Routes>
            </Suspense>
          </DriverRuntimeBoundary>
        </RouteMetadataContext.Provider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
