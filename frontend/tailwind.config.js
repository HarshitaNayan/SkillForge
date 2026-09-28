/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#111111",
        surface: "#181818",
        surface2: "#202020",
        ink: "#F5F1EA",
        muted: "#A7A19A",
        wine: "#7A263A",
        winedark: "#551827",
        copper: "#B88952",
        border: "#303030",
      },
      fontFamily: {
        display: ["'Fraunces'", "serif"],
        body: ["'Inter'", "sans-serif"],
      },
    },
  },
  plugins: [],
}
