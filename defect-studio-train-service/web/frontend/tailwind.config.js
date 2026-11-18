/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}', '../../packages/*/src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class', // 클래스 기반 다크 모드
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eef2ff', 100: '#e0e7ff', 200: '#c7d2fe', 300: '#a5b4fc',
          400: '#818cf8', 500: '#6366f1', 600: '#4f46e5', 700: '#4338ca',
          800: '#3730a3', 900: '#312e81', 950: '#1e1b4b'
        },
        dark: {
          100: '#1e293b', 200: '#0f172a', 300: '#020617'
        },
        light: {
          50: '#f9fafb', 100: '#ffffff'
        }
      },
      keyframes: {
        'panel-in': { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'none' } },
      },
      animation: { 'panel-in': 'panel-in 180ms ease-out' },
    }
  },
  plugins: []
};