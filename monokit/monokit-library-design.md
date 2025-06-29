# 🧩 MonoKit Component Library Design

## 🎯 Vision
Build MonoKit as a standalone React component library for audio conversation review interfaces, using the current Electron app as a **reference implementation** to guide the design.

---

## 📋 Approach

### Current Electron App = Reference Implementation
- **Keep as-is:** The current `call-reviewer` Electron app works perfectly as a demo
- **Extract patterns:** Use it to understand component requirements and interactions
- **Design API:** Create clean React component interfaces based on what works

### MonoKit Library = Reusable Components
- **Separate package:** Build as standalone npm package
- **Component library:** Modular, importable React components
- **Design system:** Consistent grayscale aesthetic and interactions

---

## 🗂️ Proposed Structure

```
monokit/
├── call-reviewer-demo/          # Current Electron app (preserved)
│   ├── main.js
│   ├── renderer/index.html
│   ├── public/
│   └── package.json
├── packages/
│   └── monokit/                 # New component library
│       ├── src/
│       │   ├── components/
│       │   ├── hooks/
│       │   ├── types/
│       │   └── index.ts
│       ├── dist/
│       ├── package.json
│       └── README.md
└── examples/                    # Usage examples
    ├── react-demo/
    └── next-demo/
```

---

## 🧱 Component API Design

Based on the current Electron app's functionality, design these components:

### `<Header>`
```typescript
interface HeaderProps {
  metadata: {
    date: string;
    duration: string; 
    callId: string;
  };
  summary?: {
    text: string;
    isLoading?: boolean;
  };
  className?: string;
}
```

### `<AudioTimeline>`
```typescript
interface AudioTimelineProps {
  duration: number;
  currentTime: number;
  segments: SpeakingSegment[];
  functionMarkers: FunctionMarker[];
  onSeek: (time: number) => void;
  onPlayPause: () => void;
  isPlaying: boolean;
  playbackRate: number;
  onRateChange: (rate: number) => void;
}
```

### `<Transcript>`
```typescript
interface TranscriptProps {
  data: TranscriptLine[];
  highlightTime?: number;
  onLineClick: (time: number) => void;
  className?: string;
}
```

### `<FunctionCallsPanel>`
```typescript
interface FunctionCallsPanelProps {
  calls: FunctionCall[];
  onCallClick: (time: number) => void;
  className?: string;
}
```

### `<LogsViewer>`
```typescript
interface LogsViewerProps {
  logs: string[];
  autoScroll?: boolean;
  maxHeight?: number;
  className?: string;
}
```

---

## 🎨 Design System

Extract the visual patterns from the current app:

### Color Palette (from current CSS)
```typescript
const colors = {
  bg: {
    primary: '#f8fafc',
    secondary: '#ffffff', 
    tertiary: '#f1f5f9'
  },
  border: '#e2e8f0',
  text: {
    primary: '#0f172a',
    secondary: '#475569',
    muted: '#64748b'
  },
  accent: {
    blue: '#3b82f6',
    red: '#ef4444',
    green: '#10b981',
    orange: '#f59e0b'
  }
};
```

### Typography
```typescript
const typography = {
  fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  fontSizes: {
    xs: '0.75rem',
    sm: '0.875rem', 
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.75rem'
  }
};
```

---

## 🔧 Technical Implementation

### 1. Package Setup
```json
{
  "name": "monokit",
  "version": "0.1.0",
  "description": "Minimalist greyscale components for audio conversation review",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "files": ["dist"],
  "peerDependencies": {
    "react": ">=16.8.0",
    "react-dom": ">=16.8.0"
  },
  "devDependencies": {
    "@types/react": "^18.0.0",
    "typescript": "^5.0.0",
    "tailwindcss": "^3.0.0",
    "tsup": "^7.0.0"
  }
}
```

### 2. Build Configuration (tsup)
```typescript
// tsup.config.ts
export default {
  entry: ['src/index.ts'],
  format: ['cjs', 'esm'],
  dts: true,
  sourcemap: true,
  external: ['react', 'react-dom'],
  injectStyle: true,
};
```

### 3. Component Architecture
```typescript
// src/index.ts
export { Header } from './components/Header';
export { AudioTimeline } from './components/AudioTimeline'; 
export { Transcript } from './components/Transcript';
export { FunctionCallsPanel } from './components/FunctionCallsPanel';
export { LogsViewer } from './components/LogsViewer';

// Hooks
export { useAudioPlayer } from './hooks/useAudioPlayer';
export { useTranscriptHighlight } from './hooks/useTranscriptHighlight';

// Types
export type * from './types';
```

---

## 🧪 Development Workflow

### Phase 1: Extract Component Patterns
1. **Analyze current HTML/CSS/JS** - understand interactions and state management
2. **Define TypeScript interfaces** - based on current data structures
3. **Create component mockups** - static React components matching current design

### Phase 2: Build Interactive Components  
1. **Audio timeline component** - most complex, handles playback and seeking
2. **Transcript component** - with highlighting and click-to-seek
3. **Function calls panel** - timestamped code blocks
4. **Header and logs** - simpler presentational components

### Phase 3: Integration & Hooks
1. **Audio playback hook** - manages audio state and timeline sync
2. **Data loading hooks** - for transcript and function call data
3. **Integration testing** - ensure components work together

### Phase 4: Polish & Examples
1. **Styling refinement** - perfect the grayscale aesthetic
2. **React demo app** - showing MonoKit components in action
3. **Documentation** - usage examples and API docs

---

## 📚 Usage Example

The goal is to enable this kind of clean API:

```jsx
import { 
  Header, 
  AudioTimeline, 
  Transcript, 
  FunctionCallsPanel,
  useAudioPlayer 
} from 'monokit';

function CallReviewApp() {
  const audio = useAudioPlayer('/path/to/audio.wav');
  
  return (
    <div className="min-h-screen bg-neutral-50 p-6">
      <Header 
        metadata={{ date: '...', duration: '...', callId: '...' }}
        summary={{ text: 'Customer support call resolved...' }}
      />
      
      <AudioTimeline 
        duration={audio.duration}
        currentTime={audio.currentTime}
        segments={transcriptData}
        functionMarkers={functionCalls}
        onSeek={audio.seekTo}
        onPlayPause={audio.togglePlay}
        isPlaying={audio.isPlaying}
      />
      
      <div className="grid grid-cols-2 gap-6">
        <Transcript 
          data={transcriptData}
          highlightTime={audio.currentTime}
          onLineClick={audio.seekTo}
        />
        <FunctionCallsPanel 
          calls={functionCalls}
          onCallClick={audio.seekTo}
        />
      </div>
    </div>
  );
}
```

---

## 🎯 Success Metrics

- [ ] **Clean API:** Components are easy to import and use
- [ ] **Visual consistency:** Matches the current Electron app's design
- [ ] **TypeScript support:** Full type safety and IntelliSense
- [ ] **Flexible:** Works in React, Next.js, Vite, or other React apps
- [ ] **Documented:** Clear examples and API documentation
- [ ] **Tested:** Components work reliably together

---

## 💡 Key Insight

The current Electron app **proves the design works**. Now we just need to extract that working design into reusable React components that other developers can `npm install` and use in their own audio review applications. 