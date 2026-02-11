/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#e8f2fb',
          100: '#c8e0f5',
          200: '#9ac8ed',
          300: '#5da8e0',
          400: '#0e96da',
          500: '#0a6cc3',
          600: '#0960ad',
          700: '#085ba6',
          800: '#083782',
          900: '#062c68',
          950: '#041d47',
        },
        accent: {
          50: '#fbf8ed',
          100: '#f5edcf',
          200: '#eee0ad',
          300: '#e3cf84',
          400: '#d3bd6d',
          500: '#c4a94e',
          600: '#a88d3a',
          700: '#8a7230',
          800: '#6d5a27',
          900: '#50421d',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'soft': '0 2px 8px 0 rgba(8, 55, 130, 0.06)',
        'soft-md': '0 4px 16px 0 rgba(8, 55, 130, 0.08)',
        'soft-lg': '0 8px 24px 0 rgba(8, 55, 130, 0.10)',
      },
      keyframes: {
        'pulse-ring': {
          '0%': { boxShadow: '0 0 0 0 rgba(10, 108, 195, 0.3)' },
          '70%': { boxShadow: '0 0 0 6px rgba(10, 108, 195, 0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(10, 108, 195, 0)' },
        },
      },
      animation: {
        'pulse-ring': 'pulse-ring 1.5s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
