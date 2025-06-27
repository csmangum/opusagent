# MonoKit - Call Analysis UI

A minimalist, grayscale UI kit for call analysis and conversation review built with React, TailwindCSS, and Electron.

## ✨ Features

- **Minimalist Design**: Clean, grayscale aesthetic with modern typography
- **Composable Components**: Timeline, summary, logs, transcript, and function call cards
- **Audio Timeline**: Interactive waveform visualization with markers and playback controls
- **Transcript Viewer**: Scrollable conversation display with click-to-jump functionality
- **Function Call Inspector**: Expandable JSON snippets with color-coded status indicators
- **System Logs**: Filterable log viewer with different severity levels
- **Responsive Layout**: Grid-based layout that adapts to different screen sizes

## 🚀 Quick Start

### Prerequisites

- Node.js 16+ and npm
- Git

### Installation

1. **Install dependencies:**
   ```bash
   cd monokit
   npm install
   ```

2. **Build CSS and start development:**
   ```bash
   npm run dev
   ```

3. **Or build for production:**
   ```bash
   npm run build
   npm run electron
   ```

## 🧱 Components

### Core Components

| Component | Purpose |
|-----------|---------|
| `Header` | Call metadata display with status indicators |
| `SummaryBox` | LLM-generated call summaries |
| `AudioTimeline` | Waveform visualization with interactive markers |
| `Transcript` | Conversation display with speaker identification |
| `FunctionCallBox` | API call monitoring with expandable details |
| `LogsViewer` | System logs with filtering and timestamps |

### Component Usage

```jsx
import { Header, AudioTimeline, SummaryBox, Transcript } from './components'

function CallReviewPage() {
  return (
    <div className="p-8 bg-neutral-50 min-h-screen">
      <Header date="..." duration="..." id="..." status="..." />
      <SummaryBox text="..." />
      <AudioTimeline
        duration={165}
        onJump={handleTimeJump}
        markers={[...]}
      />
      <div className="grid grid-cols-2 gap-6 mt-8">
        <Transcript data={transcriptData} />
        <FunctionCallBox calls={functionCalls} />
      </div>
      <LogsViewer logs={systemLogs} />
    </div>
  )
}
```

## 🎨 Design System

### Colors

```css
neutral: {
  50: "#f9f9f9",   /* Background */
  100: "#f2f2f2",  /* Light elements */
  300: "#dcdcdc",  /* Borders */
  600: "#2e2e2e",  /* Text */
  800: "#1a1a1a",  /* Dark elements */
  900: "#111111"   /* Darkest */
}
```

### Typography

- **Font**: Inter (system fallback: system-ui, sans-serif)
- **Font features**: Improved readability with OpenType features

### Components Styling

- **Cards**: `bg-white border border-neutral-300 rounded-lg shadow-sm`
- **Primary buttons**: `bg-neutral-900 text-white hover:bg-neutral-800`
- **Secondary buttons**: `bg-neutral-100 text-neutral-900 hover:bg-neutral-200`

## 📁 Project Structure

```
monokit/
├── src/
│   ├── components/
│   │   ├── Header.jsx
│   │   ├── SummaryBox.jsx
│   │   ├── AudioTimeline.jsx
│   │   ├── Transcript.jsx
│   │   ├── FunctionCallBox.jsx
│   │   └── LogsViewer.jsx
│   ├── styles/
│   │   └── input.css
│   ├── App.jsx
│   └── index.js
├── public/
│   ├── transcript.json
│   ├── functions.json
│   └── styles.css (generated)
├── renderer/
│   └── index.html
├── main.js (Electron main process)
├── preload.js (Electron preload script)
├── package.json
├── tailwind.config.js
└── webpack.config.js
```

## 🛠 Development

### Scripts

- `npm run dev` - Start development with hot reload
- `npm run build` - Build for production
- `npm run build-css` - Build Tailwind CSS
- `npm run build-js` - Build React components
- `npm run electron` - Start Electron app

### Data Format

#### Transcript Data
```json
{
  "id": 1,
  "timestamp": "00:02",
  "speaker": "Agent|Customer",
  "message": "Conversation text..."
}
```

#### Function Call Data
```json
{
  "id": 1,
  "timestamp": "00:12",
  "function": "function_name",
  "parameters": {...},
  "result": {
    "status": "success|error|pending",
    ...
  }
}
```

#### Log Data
```json
{
  "timestamp": "00:01:234",
  "level": "INFO|DEBUG|WARN|ERROR",
  "message": "Log message..."
}
```

## 🔧 Customization

### Theming

Modify `tailwind.config.js` to customize colors, fonts, and spacing:

```js
theme: {
  extend: {
    colors: {
      // Add your brand colors
      brand: {
        primary: '#your-color',
        secondary: '#your-color'
      }
    }
  }
}
```

### Adding Components

1. Create new component in `src/components/`
2. Import and use in `App.jsx`
3. Style with Tailwind classes

## 📦 Integration

### Electron Integration

The app is built as an Electron desktop application but components can be used in:

- **Web apps**: Import components directly
- **Next.js**: Add to pages or components
- **Vite**: Use as standard React components
- **Other React apps**: Copy component files

### API Integration

Replace sample data with real API calls:

```jsx
// Replace static data with API calls
useEffect(() => {
  fetchTranscriptData().then(setTranscriptData);
  fetchFunctionCalls().then(setFunctionCalls);
  fetchSystemLogs().then(setLogs);
}, []);
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests if needed
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

Built with ❤️ for clean, functional call analysis interfaces.