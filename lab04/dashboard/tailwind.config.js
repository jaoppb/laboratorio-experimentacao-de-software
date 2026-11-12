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
        github: {
          dark: '#0d1117',
          darker: '#010409',
          card: '#161b22',
          border: '#30363d',
          text: '#c9d1d9',
          muted: '#8b949e',
          accent: '#2f81f7',
          success: '#238636',
          warning: '#d29922',
          danger: '#f85149',
          purple: '#a371f7',
        },
        okabe: {
          orange: '#E69F00',
          skyBlue: '#56B4E9',
          bluishGreen: '#009E73',
          yellow: '#F0E442',
          blue: '#0072B2',
          vermilion: '#D55E00',
          reddishPurple: '#CC79A7',
          black: '#000000',
        },
      },
    },
  },
  plugins: [],
}
