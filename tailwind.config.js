/** Tailwind CSS — rode "npm run css" para recompilar static/css/app.css após mudar os templates. */
module.exports = {
  darkMode: "class",
  content: ["./templates/**/*.html", "./contas/**/*.py", "./notas/**/*.py"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
    },
  },
  safelist: ["selo-ok", "selo-parcial", "selo-erro"],
  plugins: [],
};
