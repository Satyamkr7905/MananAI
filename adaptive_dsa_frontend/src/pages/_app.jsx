import "@/styles/globals.css";
import Head from "next/head";
import { Inter } from "next/font/google";
import { Toaster } from "react-hot-toast";

import { GoogleOAuthProvider } from "@react-oauth/google";

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

export default function App({ Component, pageProps }) {
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
    return <GoogleOAuthProvider clientId={googleClientId}>{tree}</GoogleOAuthProvider>;
  }
  return tree;
}
