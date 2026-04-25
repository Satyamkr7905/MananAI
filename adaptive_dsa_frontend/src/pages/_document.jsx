import { Head, Html, Main, NextScript } from "next/document";

const API_ORIGIN = (() => {
  const raw = (process.env.NEXT_PUBLIC_API_BASE || "").trim();
  if (!raw) return null;
  try {
    return new URL(raw).origin;
  } catch {
    return null;
  }
})();

export default function Document() {
  return (
    <Html lang="en" className="h-full">
      <Head>
        {API_ORIGIN && (
          <>
            <link rel="preconnect" href={API_ORIGIN} crossOrigin="anonymous" />
            <link rel="dns-prefetch" href={API_ORIGIN} />
          </>
        )}
      </Head>
      <body className="h-full">
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
