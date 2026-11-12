/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        fintech: {
          darkest: '#0B0F17',
          dark: '#111827',
          card: '#161F30',
          border: '#1E293B',
          hover: '#1F293D',
          accent: '#38BDF8',
          accentDark: '#0284C7',
          up: '#10B981',
          down: '#EF4444',
          neutral: '#94A3B8'
        }
      }
    },
  },
  plugins: [],
}

