# ✅ Goals for Your UI Library

### 🧩 Core Features

* Minimalist, grayscale **aesthetic**
* Clean layout system (grid/flex)
* **Composable components**: timeline, summary, logs, transcript, function call cards
* Easy theming / project branding
* Plug-and-play in Electron, React, or Svelte projects

---

## 🗂️ Suggested Structure

```
ui-kit/
├── components/
│   ├── Header.tsx
│   ├── Timeline.tsx
│   ├── SummaryBox.tsx
│   ├── Transcript.tsx
│   ├── FunctionCallBox.tsx
│   └── LogsViewer.tsx
├── styles/
│   ├── base.css
│   └── theme.css
├── index.ts
├── tailwind.config.js (optional)
└── README.md
```

---

## 🧱 Framework Choices

### ✅ Best for you: **React + TailwindCSS**

Why:

* Tailwind gives you pixel-level control with consistent design
* React makes composing timelines, cards, logs trivial
* Compatible with Electron, Next.js, Vite, etc.

---

## 🧠 Base Components to Build

| Component         | Purpose                                   |
| ----------------- | ----------------------------------------- |
| `Header`          | Title, metadata, right-aligned summary    |
| `AudioTimeline`   | Waveform, markers, playback controls      |
| `Transcript`      | Scrollable chat, click-to-jump            |
| `FunctionCallBox` | Timestamped JSON snippets, color-coded    |
| `LogsViewer`      | VAD/system logs, scrollable + timestamped |
| `SummaryBox`      | LLM-generated text, or placeholder box    |

---

## ⚙️ Setup (React + Tailwind)

```bash
npm init -y
npm install react react-dom tailwindcss
npx tailwindcss init
```

### `tailwind.config.js`

```js
module.exports = {
  content: ['./components/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        neutral: {
          50: "#f9f9f9",
          100: "#f2f2f2",
          300: "#dcdcdc",
          600: "#2e2e2e"
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif']
      }
    }
  }
}
```

---

## 🧪 Usage Example in a Project

```jsx
import { Header, AudioTimeline, SummaryBox, Transcript } from 'my-ui-kit'

function CallReviewPage() {
  return (
    <div className="p-8 bg-neutral-50 min-h-screen">
      <Header date="..." duration="..." id="..." />
      <SummaryBox text="..." />
      <AudioTimeline
        waveformData={...}
        onJump={time => ...}
        markers={[...]}
      />
      <div className="grid grid-cols-2 gap-6 mt-8">
        <Transcript data={...} />
        <FunctionCallBox calls={...} />
      </div>
      <LogsViewer logs={...} />
    </div>
  )
}
```
