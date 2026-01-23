# Brain Trust v2.0 - Monorepo Structure

```
brain-trust-v2/
├── frontend/                   # Next.js 14 (App Router)
│   ├── app/
│   │   ├── layout.tsx         # Root layout with Grid background
│   │   ├── page.tsx           # Dashboard / Workflow list
│   │   └── workflow/
│   │       └── [id]/
│   │           └── page.tsx   # The Agent Canvas (React Flow)
│   ├── components/
│   │   ├── nodes/
│   │   │   └── AgentNode.tsx  # CUSTOM NODE: HUD aesthetic
│   │   ├── ui/                # Shadcn/UI components
│   │   │   ├── card.tsx
│   │   │   ├── button.tsx
│   │   │   └── badge.tsx
│   │   └── Canvas.tsx         # Main React Flow wrapper
│   ├── lib/
│   │   ├── api.ts             # Calls to FastAPI
│   │   └── socket.ts          # WebSocket client for logs
│   ├── public/
│   └── package.json
│
├── backend/                    # FastAPI Execution Engine
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py      # Endpoints: /run-workflow, /agents
│   │   │   └── websockets.py  # Real-time log streaming
│   │   ├── core/
│   │   │   └── workflow_parser.py # GRAPH ENGINE: JSON -> CrewAI
│   │   ├── tools/
│   │   │   └── drive_tool.py  # Google Drive "Librarian"
│   │   └── main.py            # App entry point
│   ├── requirements.txt
│   └── .env
│
├── database/                   # Supabase / SQL
│   ├── migrations/
│   │   └── 0001_init.sql      # Schema definitions
│   └── seed.sql               # Default agents/templates
│
└── README.md
```
