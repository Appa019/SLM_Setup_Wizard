/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      borderRadius: {
        DEFAULT: '1px',
        sm: '0px',
        md: '2px',
        lg: '3px',
        xl: '4px',
      },
      colors: {
        surface: {
          50:  '#f7f8f9',
          100: '#f0f2f4',
          200: '#e4e7eb',
          300: '#d1d5db',
        },
        accent: {
          50:  '#eff3fb',
          100: '#dbe5f7',
          400: '#5b7ec5',
          500: '#3d63ae',
          600: '#2f529a',
          700: '#244285',
        },
        teal: {
          400: '#22d3ee',
          500: '#0ea5e9',
          600: '#0284c7',
        },
        success: { 50: '#f0faf4', 600: '#16a34a', 700: '#15803d' },
        warning: { 50: '#fffbeb', 600: '#d97706' },
        danger:  { 50: '#fef2f2', 600: '#dc2626' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
        display: ['Space Mono', 'JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px 0 rgb(0 0 0 / 0.04)',
        'card-md': '0 1px 4px 0 rgb(0 0 0 / 0.06)',
      },
      backgroundImage: {
        'dot-grid-light': 'radial-gradient(circle, #e4e7eb 0.5px, transparent 0.5px)',
      },
      backgroundSize: {
        'dot-16': '16px 16px',
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
}
