import type { Metadata } from "next";
import "./globals.css";
import MainLayout from "@/components/layout/MainLayout";

export const metadata: Metadata = {
  title: "Investment Manager",
  description: "Investment portfolio management and research platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        <MainLayout>{children}</MainLayout>
      </body>
    </html>
  );
}
