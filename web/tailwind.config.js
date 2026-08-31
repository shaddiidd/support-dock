/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./public/index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14222b",
        muted: "#5b6b73",
        paper: "#f4efe6",
        surface: "#fffdf9",
        line: "#d7cfc3",
        harbor: {
          DEFAULT: "#0b3d4a",
          deep: "#072c36",
        },
        copper: "#c9842a",
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        card: "0 18px 50px rgba(7, 44, 54, 0.12)",
      },
    },
  },
  plugins: [],
};
