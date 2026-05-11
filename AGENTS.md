# AGENTS.md

## Dependency Constraints — STRICT LOCK
- Do NOT execute package managers (npm install, pnpm add, pip install)
- Do NOT modify package.json, pnpm-lock.yaml, or any dependency manifests
- Construct solutions using ONLY dependencies already in the root manifest
- If a dependency is missing, document it in a comment and proceed without it

### Available Dependencies
No dependencies found in package.json

## Build Artifacts — NEVER COMMIT
- Do NOT commit: dist/, build/, *.log, verification*, node_modules/
- Do NOT run npm run dev or npm run build (the CI pipeline handles this)
- Do NOT create screenshots, output files, or verification artifacts

## Code Standards
- TypeScript strict mode where applicable
- React components must not exceed 300 lines — split into sub-components
- Use named exports only (export function X, not export default)
  This prevents naming mismatches when parallel agents import each other's work
- Tailwind CSS for all styling — no inline styles, no CSS modules, no styled-components
- All component files go in src/components/
- All utility files go in src/utils/
- All context/provider files go in src/context/
- All type definitions go in src/types/

## Design System
- Follow DESIGN.md if present in the repository root
- Dark theme default: gray-900 bg, gray-800 cards, white text, gray-400 secondary
- Primary: blue-500, Success: green-500, Danger: red-500, Warning: amber-500
- Card style: rounded-2xl, shadow-lg, p-6
- Font: system default (Inter when available)
- Mobile responsive: stack on small screens, grid on desktop

## Project Structure
(run background sync for annotated directory structure)

## Parallel Execution Awareness
- You are one of multiple agents working on this repo simultaneously
- Do NOT modify src/App.jsx, src/main.jsx, or routing files
- Create ONLY the files specified in your task description
- Do NOT restructure, rename, or move existing files
- If you need to import from a sibling component that may not exist yet,
  use the exact name specified in the task description

## Testing
- Verify your changes compile: ensure no TypeScript/JSX errors
- Do not modify existing test files unless explicitly instructed
- Do not add test files unless explicitly instructed
