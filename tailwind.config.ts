import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Base surfaces
        bg: "#0A0A0C",
        surface: "#131316",
        border: "#232326",

        // Text
        "text-primary": "#F2F2F3",
        "text-secondary": "#8B8B90",

        // Status palette (mirrors CSS variables for use in className)
        "status-decided": "#34D399",
        "status-committed": "#60A5FA",
        "status-discussed": "#FBBF24",
        "status-conflict": "#F87171",
        "status-unknown": "#9CA3AF",
      },
      fontFamily: {
        sans: ["Inter Variable", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono Variable", "JetBrains Mono", "ui-monospace", "monospace"],
        display: ["Space Grotesk Variable", "Space Grotesk", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      fontSize: {
        // Design-system scale (rem-based, px shown as reference)
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }], // 10px
        xs: ["0.75rem", { lineHeight: "1rem" }],         // 12px
        sm: ["0.875rem", { lineHeight: "1.25rem" }],     // 14px
        base: ["1rem", { lineHeight: "1.5rem" }],        // 16px
        lg: ["1.125rem", { lineHeight: "1.75rem" }],     // 18px
        xl: ["1.25rem", { lineHeight: "1.75rem" }],      // 20px
        "2xl": ["1.5rem", { lineHeight: "2rem" }],       // 24px
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }],  // 30px
        "4xl": ["2.25rem", { lineHeight: "2.5rem" }],    // 36px
        "5xl": ["3rem", { lineHeight: "1" }],            // 48px
        "6xl": ["3.75rem", { lineHeight: "1" }],         // 60px
        "7xl": ["4.5rem", { lineHeight: "1" }],          // 72px
      },
      borderRadius: {
        DEFAULT: "0.375rem",
        sm: "0.25rem",
        md: "0.375rem",
        lg: "0.5rem",
        xl: "0.75rem",
        "2xl": "1rem",
      },
      boxShadow: {
        // Layered shadows for depth on dark surfaces
        "surface-sm": "0 1px 2px 0 rgba(0,0,0,0.5)",
        surface: "0 2px 8px 0 rgba(0,0,0,0.6)",
        "surface-lg": "0 8px 32px 0 rgba(0,0,0,0.7)",
        // Glow helpers for status accents
        "glow-decided": "0 0 12px 0 rgba(52,211,153,0.25)",
        "glow-committed": "0 0 12px 0 rgba(96,165,250,0.25)",
        "glow-discussed": "0 0 12px 0 rgba(251,191,36,0.25)",
        "glow-conflict": "0 0 12px 0 rgba(248,113,113,0.25)",
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease forwards",
        "slide-up": "slideUp 0.35s cubic-bezier(0.16,1,0.3,1) forwards",
        "pulse-slow": "pulse 3s cubic-bezier(0.4,0,0.6,1) infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
