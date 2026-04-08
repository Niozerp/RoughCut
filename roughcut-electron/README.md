# RoughCut Electron

AI-powered media asset management and rough cut generation for DaVinci Resolve editors.

## Features

- **Three-Panel Interface**: Media Browser | Timeline Workspace | Format Templates
- **Visual Asset Discovery**: Browse 10,000+ assets with instant search
- **AI-Powered Rough Cut Generation**: Generate timelines from transcripts
- **Seamless Resolve Integration**: One-click handoff to DaVinci Resolve
- **Dark Mode UI**: Matches Resolve's aesthetic

## Tech Stack

- **Framework**: Electron + React + TypeScript
- **UI Library**: shadcn/ui (Radix UI + Tailwind CSS)
- **Styling**: Tailwind CSS with zinc color scale
- **Icons**: Lucide React

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Run in development mode
npm run dev

# Build for production
npm run build
```

### Development

The app uses a three-panel layout:

1. **Left Panel (320px)**: Media Browser with tabs for Music, SFX, VFX
2. **Center Panel (flex)**: Timeline Workspace with preview and AI suggestions
3. **Right Panel (280px)**: Format Templates with generation controls

### Project Structure

```
roughcut-electron/
├── electron/
│   ├── main.ts           # Electron main process
│   └── preload.ts        # IPC preload script
├── src/
│   ├── components/ui/    # shadcn/ui components
│   ├── features/
│   │   ├── media-browser/
│   │   ├── timeline/
│   │   └── format-templates/
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── tailwind.config.js
└── vite.config.ts
```

## Design System

### Colors

- **Background**: #0a0a0f (zinc-950)
- **Foreground**: #fafafa (white)
- **Primary**: #f59e0b (amber) - actions, buttons
- **Secondary**: #8b5cf6 (violet) - AI elements
- **Resolve Status**:
  - Connected: #22c55e (green)
  - Connecting: #f59e0b (amber)
  - Disconnected: #ef4444 (red)

### Typography

- **Font**: Inter (Google Fonts)
- **Type Scale**: 12px to 30px
- **Weights**: 400 (normal), 500 (medium), 600 (semibold), 700 (bold)

### Spacing

- **Base Unit**: 4px
- **Panels**: 320px (left), 280px (right), flex (center)
- **Header**: 48px height

## shadcn/ui Components Used

- `Button` - Actions, navigation
- `Card` - Template cards, asset items
- `Tabs` - Music/SFX/VFX switching
- `ScrollArea` - Large asset lists
- `Input` - Search field
- `Badge` - Tags, status indicators
- `Tooltip` - Contextual help
- `Skeleton` - Loading states

## Integration Points

The app is designed to integrate with:

1. **Python Backend**: For media indexing and AI processing
2. **DaVinci Resolve**: Via Lua scripting bridge
3. **Notion API**: For cloud backup (optional)

## License

MIT
