import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: "#0f3460", light: "#16213e" },
        accent: "#e94560",
        bull: { bg: "#d4f5e9", text: "#0a7a4f" },
        bear: { bg: "#fde8e8", text: "#c0392b" },
      },
    },
  },
  plugins: [],
};
export default config;
