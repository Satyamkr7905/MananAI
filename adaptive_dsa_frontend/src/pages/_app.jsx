import "@/styles/globals.css";
import { useEffect } from "react";
import Head from "next/head";
import dynamic from "next/dynamic";
import { Inter } from "next/font/google";
import { Toaster } from "react-hot-toast";

import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";

// Next/font loads Inter locally with zero CLS and exposes it as a CSS var that
// the Tailwind config reads as the default sans font.
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "").trim();

// Split the Google Identity Services SDK into its own lazy chunk — it's
// ~100KB and not needed unless the user actually reaches a sign-in page
// with Google enabled.
const LazyGoogleOAuthProvider = dynamic(
  () => import("@react-oauth/google").then((m) => m.GoogleOAuthProvider),
  { ssr: false },
);

export default function App({ Component, pageProps }) {
  // Fire a cheap no-auth ping on mount so Render's free-tier dyno starts
  // warming while the user reads the landing/login page. Without this,
  // the first real API call (login / signup) pays the full cold-start
  // latency (~20-40s) which feels like the site is broken.
  useEffect(() => {
    if (!API_BASE || typeof window === "undefined") return;
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 20_000);
    fetch(`${API_BASE}/health`, { cache: "no-store", signal: ac.signal }).catch(
      () => {
        /* cold-start wake-up is best-effort */
      },
    ).finally(() => clearTimeout(t));
    return () => {
      clearTimeout(t);
      ac.abort();
    };
  }, []);

  const tree = (
    <ThemeProvider>
    <AuthProvider>
      <Head>
        <title>Adaptive DSA Tutor</title>
        <meta name="description" content="An adaptive, decision-driven tutor for Data Structures & Algorithms." />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.svg" />
      </Head>
      <div className={`${inter.variable} font-sans`}>
        <Component {...pageProps} />
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              borderRadius: "12px",
              background: "#0f172a",
              color: "#f8fafc",
              fontSize: 13,
            },
            success: { iconTheme: { primary: "#10b981", secondary: "#ecfdf5" } },
            error:   { iconTheme: { primary: "#f43f5e", secondary: "#fff1f2" } },
          }}
        />
      </div>
    </AuthProvider>
    </ThemeProvider>
  );

  if (googleClientId) {
    return <LazyGoogleOAuthProvider clientId={googleClientId}>{tree}</LazyGoogleOAuthProvider>;
  }
  return tree;
}
