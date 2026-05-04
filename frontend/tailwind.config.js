/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        surface:    '#13131a',
        background: '#0a0a0f',
        border:     '#1e1e2e',
        'border-bright': '#2e2e4e',
      },
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        body:    ['Manrope', 'sans-serif'],
      },
      animation: {
        'shimmer':      'shimmer 2s linear infinite',
        'float':        'float 6s ease-in-out infinite',
        'pulse-glow':   'pulseGlow 2s ease-in-out infinite',
        'scan':         'scan 3s linear infinite',
        'spin-slow':    'spin 8s linear infinite',
        'gradient-x':   'gradientX 4s ease infinite',
      },
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%':      { transform: 'translateY(-12px)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(124,58,237,0.3)' },
          '50%':      { boxShadow: '0 0 40px rgba(124,58,237,0.7)' },
        },
        scan: {
          '0%':   { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        gradientX: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%':      { backgroundPosition: '100% 50%' },
        },
      },
      backgroundImage: {
        'gradient-conic': 'conic-gradient(var(--conic-position), var(--tw-gradient-stops))',
      },
      backgroundSize: {
        '200%': '200%',
        '300%': '300%',
      },
    },
  },
  plugins: [],
}
