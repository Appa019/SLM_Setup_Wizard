/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      borderRadius: {
        DEFAULT: '4px',
        sm: '2px',
        md: '6px',
        lg: '8px',
        xl: '10px',
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
        success: { 50: '#f0faf4', 600: '#16a34a', 700: '#15803d' },
        warning: { 50: '#fffbeb', 600: '#d97706' },
        danger:  { 50: '#fef2f2', 600: '#dc2626' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.04)',
        'card-md': '0 2px 6px 0 rgb(0 0 0 / 0.08)',
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
}
