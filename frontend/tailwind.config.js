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
        background: '#0B0E14',
        surface: {
          DEFAULT: '#111622',
          hover: '#181F30',
          border: '#1E2638'
        },
        bullish: {
          DEFAULT: '#10B981',
          light: '#34D399',
          bg: 'rgba(16, 185, 129, 0.1)'
        },
        bearish: {
          DEFAULT: '#EF4444',
          light: '#F87171',
          bg: 'rgba(239, 68, 68, 0.1)'
        },
        neutral: {
          DEFAULT: '#64748B',
          bg: 'rgba(100, 116, 139, 0.1)'
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace']
      }
    },
  },
  plugins: [],
}
