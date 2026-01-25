# Coding Error Patterns & Solutions

> **Purpose**: Document recurring error types, causes, and solutions for future reference.

---

## 1. Missing Module Declarations in Isolated TSX Files

**Error Pattern**:
```
Cannot find module 'react' or its corresponding type declarations.
Cannot find module 'reactflow' or its corresponding type declarations.
JSX element implicitly has type 'any'
```

**Cause**: TSX/JSX files placed outside the main application directory (e.g., in `design_specs/`, `docs/`, or at project root) without proper TypeScript configuration or `node_modules`.

**Solution Options**:
- **A) Rename file**: Change `.tsx` to `.tsx.md` or `.tsx.example` so TypeScript ignores it
- **B) Exclude directory**: Add to `tsconfig.json` under `"exclude": ["design_specs"]`
- **C) Use comments**: If it's documentation, wrap code in markdown code blocks instead

**Prevention**: Keep design mockups as markdown with code blocks, not actual source files.

---

## 2. Implicit 'any' Type in Callbacks

**Error Pattern**:
```
Parameter 's' implicitly has an 'any' type.
```

**Cause**: TypeScript's `strict` or `noImplicitAny` setting requires explicit types on callback parameters when they can't be inferred.

**Solution**:
```typescript
// Before (error)
files = inner.split(',').map(s => s.trim())

// After (fixed)
files = inner.split(',').map((s: string) => s.trim())
```

**Prevention**: Always add explicit types to callback parameters when working with `strict: true`.

---

## 3. Property Does Not Exist on Type

**Error Pattern**:
```
Property 'files' does not exist on type '{ name: string; role: string; ... }'.
```

**Cause**: Trying to access/set a property that wasn't defined in the initial type or interface.

**Solution Options**:
- **A) Extend the type**: Add the missing property to the interface/type definition
- **B) Type assertion**: Use `as` keyword if property is conditionally added
- **C) Update initial data**: Add the property to the initial object with a default value

**Prevention**: Define all properties upfront in interfaces, use optional (`?`) for ones that may not always exist.

---

## 4. Empty Interface Extends Supertype

**Error Pattern**:
```
An interface declaring no members is equivalent to its supertype.
```

**Cause**: ESLint rule `@typescript-eslint/no-empty-interface` flags interfaces that just extend another without adding anything.

**Solution**:
```typescript
// Before (warning)
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

// After (fixed) - Use type alias instead
export type InputProps = React.InputHTMLAttributes<HTMLInputElement>
```

**Prevention**: Use `type` alias when no additional members are needed. Use `interface` when extending with new properties.

---

## 5. Forbidden require() in ES Modules

**Error Pattern**:
```
A `require()` style import is forbidden.
```

**Cause**: ESLint rule `@typescript-eslint/no-require-imports` forbids CommonJS `require()` in TypeScript/ES module files.

**Solution**:
```typescript
// Before (error)
plugins: [require("tailwindcss-animate")]

// After (fixed) - Use ES import
import tailwindcssAnimate from "tailwindcss-animate";
// ...
plugins: [tailwindcssAnimate]
```

**Prevention**: Always use ES6 `import` statements in `.ts`, `.tsx`, `.mjs` files.

---

## 6. Unknown @tailwind/@apply Rules (CSS Linter)

**Error Pattern**:
```
Unknown at rule @tailwind
Unknown at rule @apply
```

**Cause**: VS Code's default CSS linter doesn't recognize Tailwind CSS directives.

**Solution**: Add to VS Code settings (`.vscode/settings.json`):
```json
{
  "css.validate": false,
  "tailwindCSS.experimental.classRegex": []
}
```

Or use the Tailwind CSS IntelliSense extension which handles this automatically.

**Note**: These are editor warnings only - the code compiles and runs correctly.

---

## 7. Export Default Without Variable Assignment

**Error Pattern**:
```
Assign object to a variable before exporting as module default
```

**Cause**: ESLint prefers explicit variable declaration for clarity and debugging.

**Solution**:
```javascript
// Before (warning)
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} }
}

// After (fixed)
const config = {
  plugins: { tailwindcss: {}, autoprefixer: {} }
}
export default config
```

**Prevention**: Always assign to a named variable before exporting.

---

*Last updated: 2026-01-25*
