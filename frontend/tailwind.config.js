/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0A0E14",
        panel: "#111721",
        elevated: "#18202C",
        border: "#232D3B",
        "text-primary": "#E4E9F0",
        "text-secondary": "#8A97A8",
        teal: "#34D3C4",
        amber: "#F2A93B",
        "hfo-red": "#E24E42",
        lookalike: "#6B7DA8",
        violet: "#C04FD4",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        xs2: ["11px", "14px"],
      },
      borderRadius: {
        card: "6px",
        input: "4px",
      },
      boxShadow: {
        "slick-glow": "0 0 16px 2px currentColor",
      },
    },
  },
  plugins: [],
};
