import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0e1a",
        elevated: "#1a1f36",
        card: "#1e293b",
        splunk: "#65a637",
        "splunk-dark": "#3d6620",
        gold: "#f5b800",
        moat: "#fff4d6",
        dim: "#94a3b8",
        muted: "#64748b",
        border: "#334155",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
