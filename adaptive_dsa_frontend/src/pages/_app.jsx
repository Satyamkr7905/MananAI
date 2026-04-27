import "@/styles/globals.css";
import { useEffect } from "react";
import Head from "next/head";
import dynamic from "next/dynamic";
import { Inter } from "next/font/google";
import { Toaster } from "react-hot-toast";

import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { MascotProvider } from "@/context/MascotContext";

// next/font loads Inter locally, no CLS, exposed as a CSS var Tailwind reads.
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "").trim();

// split the Google Identity Services SDK into its own lazy chunk — it's
// ~100KB and we don't need it unless the user reaches a sign-in page with
// google enabled.
const LazyGoogleOAuthProvider = dynamic(
  () => import("@react-oauth/google").then((m) => m.GoogleOAuthProvider),
  { ssr: false },
);

export default function App({ Component, pageProps }) {
  // fire a cheap no-auth ping on mount so Render's free-tier dyno starts
  // waking up while the user reads the login page. without this, the first
  // real API call pays the full cold-start (~20-40s) and the site feels broken.
  useEffect(() => {
    if (!API_BASE || typeof window === "undefined") return;
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 20_000);
    fetch(`${API_BASE}/health`, { cache: "no-store", signal: ac.signal }).catch(
      () => {
        /* best-effort wake-up */
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
      <MascotProvider>
      <Head>
        <title>MananAI</title>
        <meta name="description" content="MananAI — an adaptive, decision-driven tutor for Data Structures & Algorithms." />
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
      </MascotProvider>
    </AuthProvider>
    </ThemeProvider>
  );

  if (googleClientId) {
    return <LazyGoogleOAuthProvider clientId={googleClientId}>{tree}</LazyGoogleOAuthProvider>;
  }
  return tree;
}
