import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        em: {
          black: "#000000",
          white: "#ffffff",
          red: "#FF0000",
          burgundy: "#8B0000",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
