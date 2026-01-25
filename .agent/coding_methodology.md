# Brain Trust Coding Methodology

> **For AI Agents**: This document defines coding standards and conventions for The Brain Trust project. Follow these guidelines to maintain consistency across agent handoffs.

---

## Project Structure

```
The Braintrust/
├── backend/           # Python FastAPI backend (CrewAI integration)
├── frontend/          # Next.js React frontend (TypeScript)
├── design_specs/      # Visual mockups and code prototypes (NOT compiled)
├── examples/          # Reference implementations
└── .agent/            # AI agent documentation and workflows
```

## File Conventions

| Extension | Purpose | TypeScript Compiled? |
|-----------|---------|---------------------|
| `.tsx` / `.jsx` | React components in `frontend/` | ✅ Yes |
| `.tsx.example` | Code mockups in `design_specs/` | ❌ No |
| `.ts` | TypeScript modules | ✅ Yes |
| `.md` | Documentation | N/A |

**Rule**: Files in `design_specs/` should use `.tsx.example` extension to prevent TypeScript compilation errors.

---

## TypeScript Standards

### Strict Mode Active
The project uses `strict: true`. Always:

1. **Add explicit types to callbacks**:
   ```typescript
   // ✅ Correct
   items.map((item: string) => item.trim())
   
   // ❌ Avoid - causes implicit 'any' error
   items.map(item => item.trim())
   ```

2. **Define all properties upfront**:
   ```typescript
   // ✅ Correct - include optional properties
   interface NodeData {
     name: string;
     files?: string[];  // Optional with ?
   }
   
   // ❌ Avoid - adding properties dynamically without type definition
   ```

3. **Use type aliases for simple extensions**:
   ```typescript
   // ✅ Correct
   export type InputProps = React.InputHTMLAttributes<HTMLInputElement>
   
   // ❌ Avoid - empty interface
   export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}
   ```

---

## Import Standards

Use ES6 imports exclusively in TypeScript/ESM files:

```typescript
// ✅ Correct
import tailwindcssAnimate from "tailwindcss-animate";

// ❌ Forbidden in .ts/.tsx/.mjs
require("tailwindcss-animate")
```

---

## Export Standards

Always assign to a named variable before exporting:

```javascript
// ✅ Correct
const config = { plugins: {} };
export default config;

// ❌ Avoid
export default { plugins: {} };
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `frontend/components/nodes/AgentNode.tsx` | Main agent node component for ReactFlow canvas |
| `frontend/app/page.tsx` | Main application page with workflow engine |
| `backend/app/main.py` | FastAPI entry point |
| `.agent/coding_errors_memory.md` | Common error patterns and solutions |

---

*Last updated: 2026-01-25*
