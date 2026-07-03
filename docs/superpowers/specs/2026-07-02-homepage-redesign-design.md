# Homepage Redesign Design Spec

## Overview
Replace the current minimal ProjectListPage with a rich dashboard homepage inspired by the design reference "首页.html", adapted to the existing dark theme.

## Architecture

### New Files (under src/pages/home/)
```
src/pages/home/
├── index.tsx            ← New ProjectListPage (composes all sections)
├── HomeNavbar.tsx       ← Logo + search bar (Ctrl+K) + new project button + avatar
├── AnnouncementBanner.tsx ← Dismissable announcement bar
├── HeroSection.tsx      ← Time-based greeting + subtitle
├── StatsRow.tsx         ← 4 stat cards (projects/words/chapters/foreshadowing)
├── ProjectGrid.tsx      ← Project card grid + filter/search/filter tags
├── CreateCards.tsx      ← 3 create entry cards (brainstorm/template/import)
├── TemplateGrid.tsx     ← 5 template recommendation cards
└── Footer.tsx           ← Site footer with links
```

### Data Flow
- ProjectGrid fetches real data via existing listProjects() API
- Stats/Templates use mock data (placeholder for future backend)
- Project creation via existing createProject() → navigates to /projects/:id
- Search/filter operates on loaded projects (client-side)

### Dark Theme Adaptation
| Reference (light) | Dark equivalent |
|---|---|
| bg: #f2f3f7 | bg-gray-950 |
| surface: #ffffff | bg-gray-900 |
| card-bg: #ffffff | bg-gray-800/90 |
| border: #dde1e8 | border-gray-700/50 |
| text: #1e293b | text-gray-100 |
| text-secondary: #5f6b7a | text-gray-400 |
| accent: #4f6ef6 | #4f6ef6 (retained) |

### Routes (unchanged)
- / → ProjectListPage (now rich dashboard)
- /projects/:id → ProjectPage (existing)
- POST /api/projects → createProject() → navigate

## Components

### HomeNavbar
- Sticky top, bg-gray-900/80 backdrop-blur
- Logo (SVG icon + StoryCAD text, accent color)
- Search input with magnifying glass icon, Ctrl+K shortcut
- 新建项目 button → triggers createProject modal
- User avatar (gradient circle with initial)

### AnnouncementBanner
- Gradient bg (dark blue/purple), dismissable
- Animated dot indicator
- Stores dismissed state in sessionStorage

### HeroSection
- Time-based greeting (上午好/下午好/晚上好)
- Wave animation on emoji
- Subtitle text in gray-400

### StatsRow
- 4 stat cards in flex row, responsive wrap
- Each: icon box + value + label
- Values update based on filtered project list

### ProjectGrid
- Section header with title + filter tags (全部/进行中/已完成/最近一周)
- Cards grid (auto-fill, minmax 270px)
- Each card: colored gradient cover + title + badge + meta + progress bar
- Empty state when search/filter yields no results
- Client-side search by title/keyword

### CreateCards
- 3 cards in 3-column grid (responsive: 1-col on mobile)
- Primary entry (脑洞) has solid border + subtle gradient
- Others have dashed border

### TemplateGrid
- 5 template cards in auto-fill grid
- Each: icon + name + description
- Click navigates to new project with template preset

### Footer
- Centered text, border-top, links

## Implementation Order
1. Create directory and component files
2. HomeNavbar (logo, search, btn, avatar)
3. HeroSection + StatsRow
4. ProjectGrid (cards + filter + search)
5. CreateCards + TemplateGrid
6. AnnouncementBanner + Footer
7. Compose in index.tsx
8. Integrate with real API (listProjects, createProject)
9. Clean up old ProjectListPage

## Non-Goals
- i18n (Chinese only for now)
- Editor page restyling (Navbar.tsx unchanged)
- Server-side search/filter
- Template system backend
