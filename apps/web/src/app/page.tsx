"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Wordmark } from "@/components/Wordmark";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/chat");
    } else if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--surface-app)",
      }}
    >
      <Wordmark size="lg" />
    </main>
  );
}
