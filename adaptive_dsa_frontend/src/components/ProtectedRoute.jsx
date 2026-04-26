// ProtectedRoute — wrap any page tree that needs an authed user.
// while `loading` we show a full-screen loader so the login page don't
// flash on refresh. once loaded, no token -> redirect to /login.

import { useEffect } from "react";
import { useRouter } from "next/router";
import { useAuth } from "@/hooks/useAuth";
import Loader from "./Loader";

export default function ProtectedRoute({ children }) {
  const { token, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !token) {
      router.replace("/login");
    }
  }, [loading, token, router]);

  if (loading || !token) {
    return (
      <div className="min-h-screen grid place-items-center bg-cream-50 dark:bg-slate-950">
        <Loader label="Loading your session..." />
      </div>
    );
  }
  return children;
}
