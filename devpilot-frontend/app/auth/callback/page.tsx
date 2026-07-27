"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setToken } from "@/lib/auth";

function CallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      setToken(token);
      router.replace("/repos");
    } else {
      router.replace("/");
    }
  }, [router, searchParams]);

  return (
    <main className="animate-fade-in flex flex-1 flex-col items-center justify-center gap-3">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-neutral-700 border-t-blue-500" />
      <p className="text-neutral-400">Signing you in…</p>
    </main>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<main className="flex flex-1 items-center justify-center" />}>
      <CallbackInner />
    </Suspense>
  );
}
