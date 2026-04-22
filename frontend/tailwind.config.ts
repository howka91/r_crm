import type { Config } from "tailwindcss"
import primeui from "tailwindcss-primeui"

export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  darkMode: ["selector", "[data-theme='dark']"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter Tight"', "Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        ym: {
          bg: "var(--bg)",
          surface: "var(--surface)",
          sunken: "var(--sunken)",
          line: "var(--line)",
          "line-soft": "var(--line-soft)",
          text: "var(--text)",
          muted: "var(--muted)",
          subtle: "var(--subtle)",
          primary: "var(--primary)",
          "primary-h": "var(--primary-h)",
          "primary-soft": "var(--primary-soft)",
          "primary-accent": "var(--primary-accent)",
          success: "var(--success)",
          "success-soft": "var(--success-soft)",
          warning: "var(--warning)",
          "warning-soft": "var(--warning-soft)",
          danger: "var(--danger)",
          "danger-soft": "var(--danger-soft)",
          info: "var(--info)",
          "info-soft": "var(--info-soft)",
        },
      },
      borderRadius: {
        xs: "7px",
        sm: "8px",
        md: "10px",
        lg: "14px",
      },
      boxShadow: {
        "ym-card": "0 1px 2px rgba(20,20,50,.04), 0 0 0 1px rgba(20,20,50,.04)",
        "ym-float": "0 6px 20px -6px rgba(20,20,50,.1), 0 1px 2px rgba(20,20,50,.04)",
        "ym-modal":
          "0 22px 48px -10px rgba(20,20,50,.22), 0 2px 6px rgba(20,20,50,.06)",
        "ym-primary":
          "0 1px 0 rgba(255,255,255,.12) inset, 0 2px 10px -2px oklch(0.38 0.10 155 / .45)",
        "ym-primary-lg": "0 6px 18px -4px oklch(0.38 0.10 155 / .5)",
        "ym-nav-active": "0 8px 20px -8px oklch(0.38 0.10 155 / .5)",
      },
      ringColor: {
        "ym-primary": "oklch(0.38 0.10 155 / .15)",
      },
      letterSpacing: {
        tightest: "-0.08em",
        "eyebrow-tight": "-0.025em",
      },
      backgroundImage: {
        "ym-nav-active":
          "linear-gradient(100deg, var(--primary) 0%, oklch(0.44 0.11 150) 100%)",
        "ym-login-brand":
          "linear-gradient(135deg, oklch(0.28 0.08 155) 0%, oklch(0.20 0.06 155) 100%)",
        "ym-login-glow":
          "radial-gradient(circle at 20% 20%, oklch(0.45 0.12 155 / .55), transparent 50%), radial-gradient(circle at 85% 75%, oklch(0.72 0.18 130 / .18), transparent 55%)",
      },
    },
  },
  plugins: [primeui],
} satisfies Config
