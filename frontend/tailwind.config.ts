import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-fraunces)", "Georgia", "serif"],
        mono:    ["var(--font-dm-mono)", "monospace"],
        sans:    ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      colors: {
        stone: {
          50:  "#F8F6F1",
          100: "#EDE9E1",
          200: "#D9D2C6",
          800: "#3D3730",
          900: "#1C1A16",
          950: "#100F0C",
        },
        gold: {
          300: "#E8C98A",
          400: "#C9A96E",
          500: "#A8844A",
        },
        ink: {
          DEFAULT: "#1C1C1E",
          muted:   "#6B6B6F",
          faint:   "#AEAEB2",
        },
        surface: {
          DEFAULT: "#F8F6F1",
          card:    "#FFFFFF",
          raised:  "#F0EDE6",
        },
      },
      animation: {
        "fade-up":     "fadeUp 0.5s ease forwards",
        "fade-in":     "fadeIn 0.4s ease forwards",
        "shimmer":     "shimmer 1.6s ease-in-out infinite",
        "count-up":    "countUp 0.8s cubic-bezier(0.22,1,0.36,1) forwards",
        "bar-fill":    "barFill 1s cubic-bezier(0.22,1,0.36,1) forwards",
        "spin-slow":   "spin 3s linear infinite",
      },
      keyframes: {
        fadeUp: {
          "0%":   { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-400px 0" },
          "100%": { backgroundPosition: "400px 0" },
        },
        barFill: {
          "0%":   { width: "0%" },
          "100%": { width: "var(--bar-width)" },
        },
      },
      boxShadow: {
        "card":    "0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.06)",
        "card-lg": "0 2px 8px rgba(0,0,0,0.06), 0 12px 40px rgba(0,0,0,0.10)",
        "glow":    "0 0 40px rgba(201,169,110,0.15)",
      },
    },
  },
  plugins: [],
};

export default config;
