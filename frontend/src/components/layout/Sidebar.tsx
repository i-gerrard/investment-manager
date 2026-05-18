"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Dashboard", icon: "□" },
  { href: "/portfolio", label: "Portfolios", icon: "⊞" },
  { href: "/portfolio/snapshots", label: "Snapshots", icon: "▣" },
  { href: "/review", label: "Review", icon: "✓" },
  { href: "/stocks", label: "Stocks", icon: "⊡" },
  { href: "/research", label: "Research", icon: "⊕" },
  { href: "/reports/morning", label: "Reports", icon: "⊟" },
  { href: "/simulation", label: "Simulation", icon: "◈" },
  { href: "/broker-sync", label: "Broker Sync", icon: "⟳" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-primary min-h-screen text-white flex flex-col">
      <div className="p-6 border-b border-white/10">
        <h1 className="text-xl font-bold tracking-tight">Investr</h1>
        <p className="text-xs text-white/50 mt-1">Investment Manager</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                active ? "bg-accent text-white" : "text-white/70 hover:bg-white/10 hover:text-white"
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
