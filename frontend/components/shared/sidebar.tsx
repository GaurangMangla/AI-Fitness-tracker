"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  
  Apple,
  BarChart3,
  Dumbbell,
  Home,
  Settings,
  
} from "lucide-react";

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/workouts", label: "Workouts", icon: Dumbbell },
  { href: "/progress", label: "Progress", icon: BarChart3 },
  { href: "/nutrition", label: "Nutrition", icon: Apple },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-1 p-2">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname.startsWith(href);
        return (
          <Link key={href} href={href}>
            <motion.div
              whileHover={{ x: 2 }}
              whileTap={{ scale: 0.97 }}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{label}</span>
              {active && (
                <motion.div
                  layoutId="sidebar-indicator"
                  className="ml-auto h-1.5 w-1.5 rounded-full bg-primary"
                />
              )}
            </motion.div>
          </Link>
        );
      })}
    </nav>
  );
}

export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-20 border-t bg-background/80 backdrop-blur-md lg:hidden">
      <div className="flex items-center justify-around py-2">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link key={href} href={href} className="flex flex-col items-center gap-0.5 px-3 py-1">
              <Icon className={cn("h-5 w-5", active ? "text-primary" : "text-muted-foreground")} />
              <span className={cn("text-[10px]", active ? "text-primary font-medium" : "text-muted-foreground")}>
                {label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
