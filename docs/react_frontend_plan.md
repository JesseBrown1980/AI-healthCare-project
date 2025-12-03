# React Frontend Architecture Plan

This document outlines the architecture, conventions, and workflows for the React frontend. It is intended to serve as the single source of truth for contributors and reviewers.

## Goals
- Deliver a reliable, accessible, and performant user interface for the AI healthcare platform.
- Standardize patterns for state management, data fetching, routing, and testing.
- Enable rapid feature development with clear boundaries and documentation.

## Tech Stack
- **Framework:** React with TypeScript and Vite (or CRA equivalent if required by tooling).
- **UI Library:** Headless UI components paired with a design system built on Tailwind CSS.
- **State Management:** React Query for server state; Redux Toolkit for complex client state (forms/wizards) only when needed.
- **Routing:** React Router v6 with nested routes and loader/actions for data prefetch where applicable.
- **Forms:** React Hook Form with Zod validators for schema-driven validation.
- **Testing:** Vitest + Testing Library for unit/component; Playwright for end-to-end flows.
- **Accessibility:** Use WAI-ARIA patterns; run axe-core linting during CI.

## Project Structure
```
frontend/
  src/
    app/           # App bootstrap, providers, routing
    components/    # Reusable, presentational components
    features/      # Domain features (one folder per feature)
    hooks/         # Shared hooks
    lib/           # Utilities (API client, analytics, i18n)
    pages/         # Top-level routes/pages
    styles/        # Global styles, Tailwind config
    tests/         # Test utilities and fixtures
```
- Each `features/<name>` folder contains `components/`, `hooks/`, `api/`, and `types.ts` as needed.
- Route components belong in `pages/` and compose feature-level components.

## Routing Strategy
- Define routes in `src/app/routes.tsx` using lazy-loaded modules.
- Nested routing for dashboard areas (e.g., `/patients/:id/*`, `/analytics/*`).
- Protect private routes via an `AuthGuard` that checks auth state and redirects to `/login`.
- Use route loaders to prefetch critical data when it improves perceived performance.

## State Management
- Prefer local component state for UI concerns (modals, inputs).
- Use React Query for server data: cache keys scoped by resource, optimistic updates for mutations, retry logic with exponential backoff.
- Introduce Redux Toolkit slices only for complex client workflows (multi-step forms, offline flows). Keep slices colocated with features.
- Derive data where possible; avoid duplicating server state in Redux.

## Data Fetching & API Layer
- API clients live in `src/lib/apiClient.ts` using `fetch` with a thin wrapper for auth headers and error handling.
- Use typed response/request contracts (`types.ts` per feature) generated from OpenAPI when available.
- Encapsulate queries/mutations inside feature folders (e.g., `features/patients/api.ts`).
- Global error boundary handles 401/403/500 responses and triggers logout or support prompts as needed.

## Authentication & Authorization
- Store tokens in HTTP-only cookies where possible; fallback to secure storage abstractions.
- On app init, hydrate auth state from a `/me` endpoint; show a skeleton until resolved.
- Guard protected routes and conditionally render navigation based on role/permission metadata.

## UI/UX & Accessibility
- Establish a design system with tokens (colors, spacing, typography) in `styles/theme.ts` and Tailwind config.
- Provide reusable components: `Button`, `Input`, `Select`, `Modal`, `Tooltip`, `DataTable`, `EmptyState`, `Skeleton`.
- Enforce accessibility with lint rules, focus management, keyboard navigation, and color-contrast checks.
- Support light/dark mode and respect OS preference via CSS media queries and a toggle stored in user settings.

## Forms & Validation
- Use React Hook Form controllers around design-system inputs.
- Validate with Zod schemas; share schemas between frontend and backend when possible.
- Display inline errors, field-level validation, and disable submission while pending.

## Internationalization (i18n)
- Integrate `react-i18next` with resource bundles per feature.
- Use ICU message syntax and avoid string concatenation.
- Default language: English; support locale detection and runtime language switching.

## Analytics & Telemetry
- Provide an `analytics` utility with a no-op implementation for local dev.
- Track page views, key actions, and performance metrics (web vitals) with user consent.
- Ensure compliance with privacy requirements; never send PHI/PII without explicit approval.

## Performance & Quality
- Code splitting for major routes; prefetch bundles for frequently used paths.
- Image optimization via responsive sizes and lazy loading.
- Prefer `Suspense` + skeletons for loading states.
- Linting: ESLint + TypeScript + Prettier; enforce via pre-commit hooks.
- Run unit tests, lint, and type checks in CI; e2e tests nightly or pre-release.

## Error Handling
- Use error boundaries around major route segments.
- Provide user-friendly error toasts and fallback UIs.
- Log errors to an observability backend with request correlation IDs.

## Security & Compliance
- Strict CSP defaults; avoid inline scripts/styles.
- Input sanitization for any HTML rendering; avoid `dangerouslySetInnerHTML` when possible.
- Keep dependencies updated; run `npm audit`/`yarn audit` regularly.

## Dev Experience
- Use absolute imports via `src/` alias.
- Storybook (optional) for component development and visual regression tests.
- Hot Module Replacement enabled for rapid feedback.

## Deployment
- Build with `npm run build`; artifacts served via CDN/edge where possible.
- Environment variables injected at build time for API base URL, analytics keys, and feature flags.
- Feature flags managed through a simple provider (e.g., LaunchDarkly or internal service) with fallbacks.

## Migration & Rollout Plan
- Phase 1: Scaffold app shell, routing, auth, and design system foundation.
- Phase 2: Implement core features (patient list/details, analytics dashboards) with React Query.
- Phase 3: Add forms/workflows (appointment scheduling, messaging) with validation and optimistic updates.
- Phase 4: Harden with testing, accessibility audits, and performance tuning before launch.

## Contribution Guidelines
- Follow naming conventions: `useX` for hooks, `XCard` for cards, `XPage` for page components.
- Keep components small, testable, and accessible.
- Update this plan if architecture decisions change; document rationale in PRs.
