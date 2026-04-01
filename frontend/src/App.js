import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Layout from "@/components/Layout";
import LoginPage from "@/pages/LoginPage";
import Dashboard from "@/pages/Dashboard";
import DeviceList from "@/pages/DeviceList";
import DeviceDetail from "@/pages/DeviceDetail";
import UserManagement from "@/pages/UserManagement";
import GlobalSettings from "@/pages/GlobalSettings";
import RouterModels from "@/pages/RouterModels";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Layout>
                  <Dashboard />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/devices"
            element={
              <ProtectedRoute>
                <Layout>
                  <DeviceList />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/devices/:id"
            element={
              <ProtectedRoute>
                <Layout>
                  <DeviceDetail />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/operators"
            element={
              <ProtectedRoute roles={["super_admin"]}>
                <Layout>
                  <UserManagement />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute roles={["super_admin", "operator"]}>
                <Layout>
                  <UserManagement />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/router-models"
            element={
              <ProtectedRoute>
                <Layout>
                  <RouterModels />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute roles={["super_admin"]}>
                <Layout>
                  <GlobalSettings />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
