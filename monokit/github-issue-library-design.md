# 🎯 Build MonoKit React Component Library

## 🧩 Overview

Create **MonoKit** as a standalone React component library for audio conversation review interfaces, using the current Electron app as our **reference implementation**.

## 📋 Current State

✅ **What we have:** Working Electron demo (`call-reviewer`) with excellent UX  
🎯 **What we need:** Reusable React components that developers can `npm install monokit`

## 🗂️ Project Structure

```
monokit/
├── call-reviewer-demo/          # Current Electron app (keep as-is)
├── packages/monokit/            # New React component library
│   ├── src/components/
│   ├── src/hooks/
│   ├── src/types/
│   └── package.json
└── examples/
    ├── react-demo/
    └── next-demo/
```

## 🧱 Components to Build

Based on the working Electron app, extract these components:

### 1. `<Header>` 
- **Reference:** Header section with call metadata and summary
- **Props:** `metadata`, `summary`, `className`

### 2. `<AudioTimeline>`
- **Reference:** Interactive timeline with playback controls
- **Props:** `duration`, `currentTime`, `segments`, `functionMarkers`, `onSeek`, `onPlayPause`
- **Most complex component** - handles audio visualization and interaction

### 3. `<Transcript>`
- **Reference:** Chat-style transcript with highlighting
- **Props:** `data`, `highlightTime`, `onLineClick`

### 4. `<FunctionCallsPanel>`
- **Reference:** Function calls with timestamps
- **Props:** `calls`, `onCallClick`

### 5. `<LogsViewer>`
- **Reference:** System logs footer
- **Props:** `logs`, `autoScroll`, `maxHeight`

## 🎨 Design System

Extract visual patterns from current app:
- **Colors:** Existing CSS custom properties → TailwindCSS utilities
- **Typography:** Inter font family, consistent sizing
- **Layout:** Grid-based, responsive design
- **Interactions:** Hover states, transitions, click behaviors

## 🔧 Technical Stack

- **Framework:** React + TypeScript
- **Styling:** TailwindCSS (migrate from current inline CSS)
- **Build:** tsup (simple, fast bundler)
- **Package:** NPM package with proper exports

## 📦 Target API

```jsx
import { Header, AudioTimeline, Transcript, useAudioPlayer } from 'monokit';

function MyCallReviewer() {
  const audio = useAudioPlayer('/audio.wav');
  
  return (
    <div className="min-h-screen bg-neutral-50 p-6">
      <Header metadata={{...}} summary={{...}} />
      <AudioTimeline {...audio} segments={segments} />
      <Transcript data={transcript} highlightTime={audio.currentTime} />
    </div>
  );
}
```

## 🛠️ Implementation Plan

### Phase 1: Foundation (Week 1)
- [ ] Setup package structure in `packages/monokit/`
- [ ] Configure TypeScript, TailwindCSS, tsup
- [ ] Define component interfaces based on current app

### Phase 2: Component Development (Week 2-3)  
- [ ] Build `Header` component (simplest)
- [ ] Build `Transcript` component  
- [ ] Build `FunctionCallsPanel` component
- [ ] Build `LogsViewer` component
- [ ] Build `AudioTimeline` component (most complex)

### Phase 3: Hooks & Integration (Week 4)
- [ ] Create `useAudioPlayer` hook
- [ ] Create `useTranscriptHighlight` hook  
- [ ] Test components working together
- [ ] Build React demo app

### Phase 4: Polish & Documentation (Week 5)
- [ ] Refine styling to match current app exactly
- [ ] Add comprehensive TypeScript types
- [ ] Create usage documentation
- [ ] Prepare for NPM publishing

## 🎯 Success Criteria

- [ ] `npm install monokit` works
- [ ] Components visually match current Electron app
- [ ] Clean TypeScript API with IntelliSense
- [ ] Works in React, Next.js, Vite projects
- [ ] Comprehensive usage examples

## 💡 Key Advantage

The current Electron app **proves this design works**. We're not designing from scratch - we're extracting proven UX patterns into reusable components. 