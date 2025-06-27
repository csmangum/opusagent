module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx}', './renderer/**/*.{html,js}'],
  theme: {
    extend: {
      colors: {
        neutral: {
          50: "#f9f9f9",
          100: "#f2f2f2",
          300: "#dcdcdc",
          600: "#2e2e2e",
          800: "#1a1a1a",
          900: "#111111"
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif']
      }
    }
  },
  plugins: []
}