import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/components/layout/AppProvider";

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
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
