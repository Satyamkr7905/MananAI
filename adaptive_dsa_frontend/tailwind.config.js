/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Inter is loaded via next/font in _app.jsx and exposes --font-inter.
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      colors: {
        /* Olive-inspired primary; used as `brand-*` across the app */
        brand: {
          50:  "#f5f6f0",
          100: "#e4e8d9",
          200: "#cad2b8",
          300: "#a8b38c",
          400: "#869463",
          500: "#6b7a47",
          600: "#556237",
          700: "#444f2d",
          800: "#383f28",
          900: "#2f3523",
        },
        /* Warm cream palette — used as the light-mode canvas to
           match the brand olive + cream look. */
        cream: {
          50:  "#faf6e8",
          100: "#f3ecd2",
          200: "#ece2b8",
          300: "#ddd09a",
          400: "#c8b97b",
          500: "#ac9f62",
          600: "#8a7f4f",
          700: "#6b633e",
          800: "#4f4930",
          900: "#3a3523",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,23,42,0.04), 0 1px 3px rgba(15,23,42,0.06)",
        soft: "0 4px 20px rgba(15,23,42,0.06)",
      },
      keyframes: {
        fadeIn: { "0%": { opacity: 0, transform: "translateY(4px)" }, "100%": { opacity: 1, transform: "translateY(0)" } },
        pulseDot: { "0%,100%": { opacity: 1 }, "50%": { opacity: 0.4 } },
      },
      animation: {
        "fade-in": "fadeIn 0.25s ease-out",
        "pulse-dot": "pulseDot 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
