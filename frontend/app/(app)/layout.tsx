"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AmbientBackground } from "@/components/shared/ambient-background";
import { BottomNav, Sidebar } from "@/components/shared/sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useCurrentUser } from "@/hooks/use-current-user";
import { clearToken, getToken } from "@/lib/auth-token";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [mounted, setMounted] = useState(false);
  const { data: user, isLoading, isError } = useCurrentUser();

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!mounted) return;
    if (!getToken() || isError) {
      clearToken();
      queryClient.clear();
      router.replace("/login");
    }
  }, [mounted, isError, queryClient, router]);

  function handleLogout() {
    clearToken();
    queryClient.clear();
    router.push("/login");
  }

  if (!mounted || !getToken() || isError) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Skeleton className="h-8 w-32" />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen">
      <AmbientBackground />

      {/* Sidebar — hidden on mobile, visible lg+ */}
      <aside className="fixed left-0 top-0 z-20 hidden h-full w-56 border-r bg-background/80 backdrop-blur-md lg:flex lg:flex-col">
        <div className="flex h-14 items-center border-b px-4">
          <span className="text-lg font-bold tracking-tight">
            <span className="text-gradient-brand">Athlyt</span>
          </span>
        </div>
        <div className="flex-1 overflow-y-auto py-2">
          <Sidebar />
        </div>
        <div className="border-t p-3 text-xs text-muted-foreground">
          {isLoading ? (
            <Skeleton className="h-4 w-28" />
          ) : (
            <span className="block truncate">{user?.profile?.name ?? user?.email}</span>
          )}
        </div>
      </aside>

      {/* Top bar — mobile only */}
      <header className="glass-card sticky top-0 z-20 flex items-center justify-between rounded-none border-x-0 border-t-0 px-4 py-3 lg:hidden">
        <span className="text-lg font-bold tracking-tight">
          <span className="text-gradient-brand">Athlyt</span>
        </span>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button variant="outline" size="sm" onClick={handleLogout} className="transition-transform active:scale-95">
            Log out
          </Button>
        </div>
      </header>

      {/* Top bar — desktop right side */}
      <header className="fixed right-0 top-0 z-20 hidden h-14 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur-md lg:left-56 lg:flex">
        <div className="flex-1" />
        {!isLoading && (
          <span className="text-sm text-muted-foreground">{user?.profile?.name ?? user?.email}</span>
        )}
        <ThemeToggle />
        <Button variant="outline" size="sm" onClick={handleLogout}>Log out</Button>
      </header>

      {/* Main content */}
      <main className="relative z-10 p-4 pb-24 pt-4 sm:p-6 sm:pb-28 lg:ml-56 lg:pb-8 lg:pt-20">
        {children}
      </main>

      {/* Bottom nav — mobile */}
      <BottomNav />
    </div>
  );
}
