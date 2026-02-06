import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
    darkMode: ["class"],
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                background: 'hsl(var(--background))',
                foreground: 'hsl(var(--foreground))',
                card: {
                    DEFAULT: 'hsl(var(--card))',
                    foreground: 'hsl(var(--card-foreground))'
                },
                popover: {
                    DEFAULT: 'hsl(var(--popover))',
                    foreground: 'hsl(var(--popover-foreground))'
                },
                primary: {
                    DEFAULT: 'hsl(var(--primary))',
                    foreground: 'hsl(var(--primary-foreground))'
                },
                secondary: {
                    DEFAULT: 'hsl(var(--secondary))',
                    foreground: 'hsl(var(--secondary-foreground))'
                },
                muted: {
                    DEFAULT: 'hsl(var(--muted))',
                    foreground: 'hsl(var(--muted-foreground))'
                },
                accent: {
                    DEFAULT: 'hsl(var(--accent))',
                    foreground: 'hsl(var(--accent-foreground))'
                },
                destructive: {
                    DEFAULT: 'hsl(var(--destructive))',
                    foreground: 'hsl(var(--destructive-foreground))'
                },
                border: 'hsl(var(--border))',
                input: 'hsl(var(--input))',
                ring: 'hsl(var(--ring))',
                chart: {
                    '1': 'hsl(var(--chart-1))',
                    '2': 'hsl(var(--chart-2))',
                    '3': 'hsl(var(--chart-3))',
                    '4': 'hsl(var(--chart-4))',
                    '5': 'hsl(var(--chart-5))'
                },
                brand: {
                    DEFAULT: '#6366F1',
                    50: '#EEF2FF',
                    400: '#818CF8',
                    500: '#6366F1',
                    600: '#4F46E5',
                },
                surface: {
                    0: 'hsl(225 15% 6%)',
                    1: 'hsl(225 15% 8%)',
                    2: 'hsl(225 14% 10%)',
                    3: 'hsl(225 13% 13%)',
                    4: 'hsl(225 12% 16%)',
                },
            },
            borderRadius: {
                lg: 'var(--radius)',
                md: 'calc(var(--radius) - 2px)',
                sm: 'calc(var(--radius) - 4px)'
            },
            boxShadow: {
                'glow-sm': '0 0 10px -3px hsl(220 70% 55% / 0.3)',
                'glow-md': '0 0 20px -5px hsl(220 70% 55% / 0.3)',
                'glow-lg': '0 0 40px -10px hsl(220 70% 55% / 0.3)',
                'glow-emerald': '0 0 20px -5px hsl(160 84% 39% / 0.3)',
                'glow-violet': '0 0 20px -5px hsl(262 83% 58% / 0.3)',
                'glow-amber': '0 0 20px -5px hsl(38 92% 50% / 0.3)',
                'elevation-1': '0 1px 3px 0 hsl(225 15% 4% / 0.5), 0 1px 2px -1px hsl(225 15% 4% / 0.5)',
                'elevation-2': '0 4px 6px -1px hsl(225 15% 4% / 0.5), 0 2px 4px -2px hsl(225 15% 4% / 0.5)',
                'elevation-3': '0 10px 15px -3px hsl(225 15% 4% / 0.5), 0 4px 6px -4px hsl(225 15% 4% / 0.5)',
            },
            fontFamily: {
                sans: ['var(--font-geist-sans)', 'system-ui', 'sans-serif'],
                mono: ['var(--font-geist-mono)', 'ui-monospace', 'monospace'],
            },
        }
    },
    plugins: [tailwindcssAnimate],
};
export default config;
