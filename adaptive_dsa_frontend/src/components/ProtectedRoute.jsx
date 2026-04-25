/**
 * ProtectedRoute — wraps any page tree that requires an authenticated user.
 *
 * While `loading` we show a full-screen loader so the login page doesn't flash
 * on refresh. Once loaded, if there's no token we redirect to /login.
 */

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
      <div className="min-h-screen grid place-items-center bg-slate-50">
        <Loader label="Loading your session..." />
      </div>
    );
  }
  return children;
}
