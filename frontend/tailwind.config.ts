import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Single-zone light theme, SaaS-support-tool style: white/near-white
        // main content, a slightly-darker-gray sidebar to set it apart, and an
        // indigo accent used sparingly (primary buttons, active states, badges).
        canvas: "#f9fafb", // main content page background (near-white)
        surface: "#ffffff", // top nav, cards (answer bubble, tables, dropdowns, login/signup)
        "surface-raised": "#eef0f3", // sidebar background, inputs, hover-fill states within white cards
        border: {
          DEFAULT: "#e5e7eb",
          subtle: "#eef0f3",
        },
        accent: {
          DEFAULT: "#4f46e5", // indigo-600 -- primary buttons, active tab/status, links
          hover: "#4338ca", // indigo-700 -- hover/pressed (darker, standard for light-theme buttons)
          muted: "#e0e7ff", // indigo-100 -- subtle accent fills
        },
        ink: {
          DEFAULT: "#111827",
          muted: "#6b7280",
          faint: "#9ca3af",
        },
      },
      borderRadius: {
        lg: "10px",
        xl: "12px",
      },
    },
  },
  plugins: [],
};

export default config;
