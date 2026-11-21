/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        display: ['Sora', '"Plus Jakarta Sans"', 'sans-serif'],
      },
      colors: {
        ink: { 950: '#060914', 900: '#0a0f1f', 800: '#111833', 700: '#1a2347', 600: '#26305c' },
        brand: { 300: '#c4b5fd', 400: '#a78bfa', 500: '#8b5cf6', 600: '#7c3aed' },
        glow: { 400: '#2dd4bf', 500: '#14b8a6' },
      },
      boxShadow: {
        glass: '0 10px 40px -10px rgba(0,0,0,0.6), inset 0 1px 0 0 rgba(255,255,255,0.06)',
        brand: '0 10px 30px -8px rgba(139,92,246,0.55)',
      },
      keyframes: {
        float: { '0%,100%': { transform: 'translate(0,0) scale(1)' }, '50%': { transform: 'translate(30px,-30px) scale(1.08)' } },
        fadeUp: { from: { opacity: 0, transform: 'translateY(10px)' }, to: { opacity: 1, transform: 'none' } },
        pop: { '0%': { transform: 'scale(.6)', opacity: 0 }, '70%': { transform: 'scale(1.08)' }, '100%': { transform: 'scale(1)', opacity: 1 } },
      },
      animation: {
        float: 'float 18s ease-in-out infinite',
        'float-slow': 'float 26s ease-in-out infinite reverse',
        'fade-up': 'fadeUp .45s ease-out both',
        pop: 'pop .5s cubic-bezier(.2,.9,.3,1.3) both',
      },
    },
  },
  plugins: [],
}
