"use client";

import { AuthProvider } from "@/lib/AuthContext";
import MainLayout from "./MainLayout";

export function AppProvider({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <MainLayout>{children}</MainLayout>
    </AuthProvider>
  );
}
