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

- **REST API**: `http://localhost:8000/api/*`, called through the typed client in `src/lib/api/`
- **WebSocket**: `ws://localhost:8000/ws/{session_id}` for real-time progress updates

Start the backend before the frontend (`cd backend && uv run sibyl --log-level INFO`).

### Generated API client

`openapi.json` and `src/lib/api/schema.d.ts` are generated from the backend's response models. Never edit them by hand.
After changing a backend route or response model, regenerate both and commit them:

```bash
npm run gen:api          # needs uv and the backend environment
```

CI fails when either file is out of date. `src/lib/api/index.ts` wraps the generated client as `api.*` calls, and
`src/lib/types.ts` aliases the generated types for components.

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
├── openapi.json               # GENERATED from the backend (npm run gen:api)
├── src/
│   ├── app/                   # App Router: root layout + providers, one route per page
│   │   ├── review/  library/  models/  gpu/
│   ├── features/              # one folder per page: its components, hooks and context
│   │   ├── review/            # review form, session (WebSocket), results
│   │   ├── library/           # stored reviews
│   │   ├── models/            # model catalog, installs (WebSocket), installed models
│   │   └── gpu/               # GPU monitor and load summary
│   ├── components/            # components shared by features
│   │   └── ui/                # shadcn/ui-style primitives
│   ├── hooks/                 # shared hooks (toasts, score scale)
│   ├── lib/
│   │   ├── api/
│   │   │   ├── index.ts       # typed `api` client
│   │   │   ├── queries.ts     # TanStack Query options for every read
│   │   │   └── schema.d.ts    # GENERATED types
│   │   ├── types.ts           # aliases of generated types
│   │   └── ...                # config, formatting, download and text helpers
│   └── __tests__/             # Vitest tests, mirroring src/ (helpers/ for render, fetch and WebSocket fakes)
└── package.json
```

## Environment Variables

Create a `.env.local` file to customize the backend URL (see `.env.local.example` for template):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

The application will use `http://localhost:8000` as the default if no environment variable is set.

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [shadcn/ui Documentation](https://ui.shadcn.com)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
