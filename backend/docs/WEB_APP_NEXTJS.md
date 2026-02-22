# Sibyl Web Application (Next.js)

## Overview

The Sibyl Web Application has been refactored to use modern web technologies:

- **Next.js 15** - React framework with App Router
- **React 19** - UI library for component-based development
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - High-quality component library built on Radix UI

## Architecture

### Frontend (Next.js)
- Located in `/web` directory
- Runs on `http://localhost:3000` by default
- Communicates with FastAPI backend via REST API and WebSocket

### Backend (FastAPI)
- Located in `/src/sibyl/web_app.py`
- Runs on `http://localhost:8000`
- Provides REST API endpoints and WebSocket for real-time updates
- CORS enabled for Next.js frontend

## Getting Started

### Prerequisites

- **Python 3.12+** (Python 3.12+ recommended) with Sibyl installed
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package installer
- **Node.js 18+** and npm
- **Ollama** installed and running with a model pulled

### Installation

1. **Install Python dependencies**:
   ```bash
   # Install uv if not already installed
   # macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

   # Install Sibyl with web dependencies
   uv pip install -e ".[web]"
   ```

2. **Install Node.js dependencies**:
   ```bash
   cd web
   npm install
   ```

### Running the Application

You need to run **both** the backend and frontend:

#### Terminal 1: Start Backend
```bash
# In the sibyl root directory
sibyl web
```

This starts the FastAPI backend on `http://localhost:8000`

#### Terminal 2: Start Frontend
```bash
# In the web directory
cd web
npm run dev
```

This starts the Next.js frontend on `http://localhost:3000`

### Usage

1. Open your browser to `http://localhost:3000`
2. Drag and drop a PDF research paper or click to browse
3. Click "Start Review"
4. Watch real-time progress as the AI reviews your paper
5. View comprehensive results with statistics and detailed feedback

## Features

### Modern UI Components (shadcn/ui)
- **Button** - Interactive buttons with multiple variants
- **Card** - Container component for content sections
- **Progress** - Real-time progress bar for review status

### Responsive Design
- Mobile-friendly layout
- Adapts to different screen sizes
- Touch-friendly for tablets

### Dark Mode
- Automatic dark mode support
- Respects system preferences

### Real-time Updates
- WebSocket connection for live progress tracking
- Instant feedback on upload and processing status

## Development

### Project Structure

```
web/
├── src/
│   ├── app/
│   │   ├── page.tsx          # Main review page
│   │   ├── layout.tsx         # Root layout
│   │   └── globals.css        # Global styles & Tailwind config
│   ├── components/
│   │   └── ui/                # shadcn/ui components
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       └── progress.tsx
│   └── lib/
│       └── utils.ts           # Utility functions (cn helper)
├── public/                    # Static assets
├── package.json
├── tsconfig.json              # TypeScript configuration
├── components.json            # shadcn/ui configuration
└── README.md
```

### Adding New shadcn/ui Components

```bash
cd web
npx shadcn@latest add <component-name>
```

For example:
```bash
npx shadcn@latest add dialog
npx shadcn@latest add dropdown-menu
```

### Customizing Styles

Edit `src/app/globals.css` to customize the color scheme:

```css
:root {
  --primary: 262 83% 58%;  /* Purple primary color */
  --secondary: 240 4.8% 95.9%;
  /* Add more custom colors */
}
```

### Building for Production

```bash
cd web
npm run build
npm start
```

## API Integration

### REST API Endpoints

The frontend communicates with these FastAPI endpoints:

- **POST /api/upload** - Upload PDF file
  ```typescript
  const formData = new FormData()
  formData.append("file", file)
  const response = await fetch("http://localhost:8000/api/upload", {
    method: "POST",
    body: formData
  })
  ```

- **GET /api/health** - Check backend status
  ```typescript
  const response = await fetch("http://localhost:8000/api/health")
  const health = await response.json()
  ```

### WebSocket

Real-time progress updates via WebSocket:

```typescript
const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`)

ws.onmessage = (event) => {
  const message = JSON.parse(event.data)

  if (message.status === "progress") {
    // Update progress bar
    setProgress(message.progress)
  } else if (message.status === "completed") {
    // Display results
    setResults(message.results)
  }
}
```

## Type Safety

The frontend uses TypeScript interfaces that match the backend Pydantic models:

```typescript
interface ReviewCriteria {
  novelty: string
  methodology: string
  results: string
  clarity: string
  impact: string
  limitations: string
  strengths: string
  overall_score: number
  recommendation: string
  detailed_feedback: string
}

interface Review {
  paper_title: string
  reviewer_model: string
  criteria: ReviewCriteria
}
```

## Troubleshooting

### Backend won't start
- Ensure Ollama is running: `ollama list`
- Check `.env` configuration
- Verify port 8000 is available

### Frontend won't start
- Check Node.js version: `node --version` (should be 18+)
- Delete `node_modules` and run `npm install` again
- Check port 3000 is available

### CORS errors
- Ensure backend is running on port 8000
- Verify CORS middleware is configured in `web_app.py`
- Check browser console for detailed error messages

### WebSocket connection fails
- Verify backend WebSocket endpoint is working
- Check firewall settings
- Ensure both frontend and backend use same protocol (http/https)

## Deployment

### Production Build

1. **Build Frontend**:
   ```bash
   cd web
   npm run build
   ```

2. **Serve Static Files**:
   You can serve the Next.js build output using:
   - Vercel (recommended for Next.js)
   - Netlify
   - Static file server

3. **Backend**:
   Deploy FastAPI backend using:
   - Docker
   - Gunicorn + Uvicorn workers
   - Cloud providers (AWS, GCP, Azure)

### Environment Variables

For production, set:

```env
# Frontend (.env.local)
NEXT_PUBLIC_API_URL=https://your-api-domain.com

# Backend
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## Benefits of Next.js/React Architecture

1. **Component Reusability** - Build modular, reusable UI components
2. **Type Safety** - TypeScript catches errors at compile time
3. **Performance** - React's virtual DOM and Next.js optimizations
4. **Developer Experience** - Hot reload, better debugging tools
5. **Ecosystem** - Access to vast React/Next.js ecosystem
6. **SEO** - Server-side rendering capabilities
7. **Maintainability** - Better code organization and testing

## Migration from Vanilla JS

The original vanilla JS implementation (`src/sibyl/static/*`) has been replaced with the Next.js app. Key improvements:

- **Before**: Single HTML file with inline JavaScript
- **After**: Component-based architecture with separate concerns

- **Before**: Manual DOM manipulation
- **After**: Declarative React components with state management

- **Before**: Custom CSS
- **After**: Tailwind CSS with shadcn/ui components

- **Before**: No type safety
- **After**: Full TypeScript type checking

## Contributing

When contributing to the web frontend:

1. Follow React/Next.js best practices
2. Use shadcn/ui components when possible
3. Maintain type safety with TypeScript
4. Test on multiple browsers and devices
5. Keep the UI responsive and accessible

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [shadcn/ui Documentation](https://ui.shadcn.com)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [TypeScript Documentation](https://www.typescriptlang.org/docs)
