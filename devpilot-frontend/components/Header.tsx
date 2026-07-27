"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch, type User } from "@/lib/api";
import { clearToken } from "@/lib/auth";
import Logo from "./Logo";

export default function Header() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    apiFetch<User>("/auth/me")
      .then(setUser)
      .catch(() => {});
  }, []);

  function handleLogout() {
    clearToken();
    router.replace("/");
  }

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between border-b border-neutral-800 bg-black/80 px-4 py-3 backdrop-blur">
      <Link
        href="/repos"
        className="hover-lift group flex items-center gap-2 font-semibold tracking-tight transition-opacity hover:opacity-80"
      >
        <span className="transition-transform duration-300 group-hover:rotate-[15deg]">
          <Logo size={26} />
        </span>
        <span className="text-gradient">DevPilot AI</span>
      </Link>

      {user && (
        <div className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="btn-press flex items-center gap-2 rounded-full py-1 pl-1 pr-3 transition-colors hover:bg-neutral-900"
          >
            {user.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.avatar_url}
                alt={user.username}
                className="h-7 w-7 rounded-full ring-0 ring-blue-500 transition-all hover:ring-2"
              />
            ) : (
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-neutral-800 text-xs">
                {user.username.slice(0, 1).toUpperCase()}
              </span>
            )}
            <span className="text-sm text-neutral-300">{user.username}</span>
            <span
              className={`text-[10px] text-neutral-600 transition-transform duration-200 ${menuOpen ? "rotate-180" : ""}`}
            >
              ▾
            </span>
          </button>

          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="animate-menu-in absolute right-0 top-full z-20 mt-2 w-40 overflow-hidden rounded-lg border border-neutral-800 bg-neutral-950 shadow-xl">
                <button
                  onClick={handleLogout}
                  className="block w-full px-3 py-2 text-left text-sm text-neutral-300 transition-colors hover:bg-neutral-900 hover:text-white"
                >
                  Log out
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </header>
  );
}
