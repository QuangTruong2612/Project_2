import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      keyframes: {
        bounce1: { "0%,80%,100%": { opacity: "0.3" }, "40%": { opacity: "1" } },
      },
      animation: {
        "dot-1": "bounce1 1.2s infinite ease-in-out",
        "dot-2": "bounce1 1.2s infinite ease-in-out 0.15s",
        "dot-3": "bounce1 1.2s infinite ease-in-out 0.3s",
      },
    },
  },
  plugins: [],
};

export default config;
