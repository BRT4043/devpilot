"use client";

import { useId } from "react";

export default function Logo({ size = 24, animated = false }: { size?: number; animated?: boolean }) {
  const gradientId = useId();

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={animated ? "animate-pulse-glow rounded-md" : ""}
    >
      <rect width="24" height="24" rx="6" fill={`url(#${gradientId})`} />
      <g stroke="white" strokeWidth="1.4" strokeLinecap="round" opacity="0.9">
        <line x1="7" y1="8" x2="17" y2="8" />
        <line x1="7" y1="8" x2="12" y2="17" />
        <line x1="17" y1="8" x2="12" y2="17" />
      </g>
      <circle cx="7" cy="8" r="2" fill="white" />
      <circle cx="17" cy="8" r="2" fill="white" />
      <circle cx="12" cy="17" r="2" fill="white" />
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse">
          <stop stopColor="#3b82f6" />
          <stop offset="1" stopColor="#7c3aed" />
        </linearGradient>
      </defs>
    </svg>
  );
}
