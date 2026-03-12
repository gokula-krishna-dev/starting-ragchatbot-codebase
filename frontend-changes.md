# Frontend Changes: Dark/Light Theme Toggle

## Overview
Added a toggle button that allows users to switch between dark and light themes with smooth transitions and localStorage persistence.

## Files Modified

### 1. `frontend/index.html`
- Added a theme toggle button with sun/moon SVG icons inside `.container`, before `.main-content`
- Button includes `aria-label` and `title` for accessibility
- Uses `id="themeToggle"` for JS binding

### 2. `frontend/style.css`
- Added `[data-theme="light"]` CSS variable overrides for all theme colors:
  - Light background (`#f8fafc`), white surface (`#ffffff`)
  - Dark text (`#0f172a`) for contrast, muted secondary text (`#64748b`)
  - Adjusted borders (`#e2e8f0`), shadows, and code block backgrounds
- Added `.theme-toggle` styles: fixed position top-right, circular button, hover/focus/active states
- Added icon visibility rules: sun icon shows in dark mode, moon icon in light mode
- Added `transition` rules on key elements for smooth 0.3s theme switching

### 3. `frontend/script.js`
- Added `themeToggle` DOM element reference
- Added `initTheme()`: reads saved theme from `localStorage`, defaults to dark, applies `data-theme` attribute on `<html>`
- Added `toggleTheme()`: switches between dark/light, saves preference to `localStorage`
- Added `updateThemeToggleLabel()`: updates `aria-label` and `title` for screen readers
- Registered click listener on theme toggle button in `setupEventListeners()`

## Design Decisions
- Theme is applied via `data-theme` attribute on `<html>` element
- All existing CSS variables are overridden in light theme, so every element adapts automatically
- localStorage persistence means the user's preference survives page reloads
- Default theme is dark (matching the existing design)
- Button is `position: fixed` with `z-index: 100` to stay visible at all times
- Inline `<script>` in `<head>` applies saved theme before first paint to prevent flash of wrong theme

## Security & Accessibility Fixes (post-review)
- Escaped HTML in `sources` array and course titles before `innerHTML` injection (XSS prevention)
- Added `aria-hidden="true"` and `focusable="false"` to SVG icons to prevent screen reader noise
- Fixed `var(--primary)` to `var(--primary-color)` in blockquote border-left
- Moved error/success message colors to CSS variables with light-theme-appropriate contrast values
