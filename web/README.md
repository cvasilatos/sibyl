# Sibyl Web Frontend

This is the Next.js frontend for the Sibyl research paper review system, built with:

- **Next.js 15** - React framework with App Router
- **React 19** - UI library  
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **shadcn/ui** - Component library

## Getting Started

### Prerequisites

- Node.js 18+
- Python backend running on `http://localhost:8000`

### Installation

```bash
npm install
```

### Development

```bash
# Start the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the app.

### Building for Production

```bash
# Build the application
npm run build

# Start production server
npm start
```

## Backend Integration

The frontend communicates with the FastAPI backend:

- **REST API**: `http://localhost:8000/api/*` for file uploads and health checks
- **WebSocket**: `ws://localhost:8000/ws/{session_id}` for real-time progress updates

Make sure the Python backend is running before starting the frontend:

```bash
# In the sibyl root directory
sibyl web
```

## Features

- Drag-and-drop PDF upload
- Real-time progress tracking
- Comprehensive review display
- Responsive design (mobile-friendly)
- Dark mode support
- Type-safe API integration

## Project Structure

```
web/
├── src/
│   ├── app/
│   │   ├── page.tsx          # Main page component
│   │   ├── layout.tsx         # Root layout
│   │   └── globals.css        # Global styles with Tailwind
│   ├── components/
│   │   └── ui/                # shadcn/ui components
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       └── progress.tsx
│   └── lib/
│       └── utils.ts           # Utility functions
├── public/                    # Static assets
└── package.json
```

## Environment Variables

Create a `.env.local` file if you need to customize the backend URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [shadcn/ui Documentation](https://ui.shadcn.com)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
