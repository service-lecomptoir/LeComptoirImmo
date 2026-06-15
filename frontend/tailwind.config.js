/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      // Couleur de marque Le Comptoir Immo (alignée sur le bleu historique).
      // Token unique pour harmoniser progressivement les surfaces primaires.
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        // Tokens de marque Le Comptoir Immo (source unique : on remplace
        // progressivement les hex en dur #0D2F5C / #F07800 dispersés).
        brand: {
          navy: '#0D2F5C',
          'navy-light': '#1A4A8A',
          teal: '#0E9F8E',
          orange: '#F07800',
        },
      },
    },
  },
  plugins: [],
}
