# 🖤 MonoKit – Minimalist Greyscale Interface Library

MonoKit is a precision-crafted UI component library for building clean, intuitive interfaces for reviewing audio-based conversations. Designed for clarity, speed, and elegance with a monochrome visual language.

---

## ✨ Design Philosophy

> A grayscale, elegantly structured interface that emphasizes clarity, spaciousness, and cognitive flow. It feels intentional, quiet, and precise—prioritizing information hierarchy and ease of comprehension over decoration.

### Visual Traits

- 🎨 **Monochrome palette** – shades of grey, not black and white
- 📐 **Minimalist structure** – only essentials, clean layout
- 🧠 **Cognitive hierarchy** – transcript, timeline, logs and metadata all feel natural
- ✍️ **Elegant typography** – `Inter`, `IBM Plex Sans`, or `Space Grotesk`
- 🪞 **Quiet interactivity** – soft hover states, subtle transitions, no visual noise

---

## 🧩 Core Components

| Component          | Description |
|-------------------|-------------|
| `Header`          | Displays call metadata (date, duration, ID) and summary slot |
| `SummaryBox`      | LLM summary placeholder with subtle visual design |
| `AudioTimeline`   | Greyscale waveform with clickable regions and markers |
| `Transcript`      | Chat-style display of agent and caller dialogue |
| `FunctionCallBox` | JSON-style code blocks with visual markers and timestamps |
| `LogsViewer`      | Terminal-style readout of backend logs with auto-scroll |

---

## 🚀 Quick Start

```bash
npm install monokit
```

```jsx
import {
  Header,
  SummaryBox,
  AudioTimeline,
  Transcript,
  FunctionCallBox,
  LogsViewer
} from 'monokit';

function CallReviewApp() {
  return (
    <div className="bg-neutral-50 min-h-screen p-6">
      <Header date="..." duration="..." id="..." />
      <SummaryBox text="LLM summary will go here..." />
      <AudioTimeline ... />
      <div className="grid grid-cols-2 gap-4 mt-6">
        <Transcript data={...} />
        <FunctionCallBox calls={...} />
      </div>
      <LogsViewer logs={...} />
    </div>
  );
}
```

---

## 🛠️ Technologies Used

- **React** (or Svelte variant coming soon)
- **TailwindCSS** (optional, easy to theme)
- WaveSurfer.js for audio waveform
- Whisper-ready and LLM-augmentable structure

---

## 🔮 Coming Soon

- Drag-and-drop file session loader
- Whisper-based real-time diarization
- LLM summary + call intent extractor
- Export to PDF
- Light/Dark mode toggle

---

## 🧘 Summary

> "A frictionless framework for building review tools that feel as clean and quiet as a thoughtfully designed studio monitor. Everything you need—nothing you don’t."

---