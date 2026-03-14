/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        primary: "#000000",
        secondary: "#8B0000",
        accent: "#FF0000",
        surface: "#111111",
        "surface-light": "#1a1a1a",
      },
    },
  },
  plugins: [],
};
