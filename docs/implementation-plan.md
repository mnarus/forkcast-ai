## implementation-plan.md

### Step-by-step build sequence (mindless micro-tasks)

#### Phase 0 — Setup (Day 1–2)
- Create repo
- Initialize React Native app
- Initialize Node.js backend
- Set up PostgreSQL database
- Create basic API endpoint (/health)

#### Phase 1 — Core data (Day 3–5)
- Create tables:
  - User
  - Meal
  - Plan
  - BehaviorLog
  - GroceryList

- Build endpoints:
  - Create user
  - Fetch meals
  - Save plan
  - Log behavior (cook / skip)

#### Phase 2 — Meal generation (Day 6–10)
- Integrate LLM API
- Create “generate weekly plan” endpoint
- Add rules:
  - Limit prep time
  - Avoid repetition
  - Match preferences

#### Phase 3 — Grocery list (Day 11–13)
- Aggregate ingredients from meals
- Group by category (produce, dairy, etc.)
- Create grocery list endpoint
- Connect to frontend

#### Phase 4 — Basic UI (Day 14–18)
- Build screens:
  - Weekly plan view
  - Meal detail
  - Grocery list

- Add actions:
  - Cook
  - Skip
  - Swap

#### Phase 5 — Feedback loop (Day 19–22)
- Store behavior logs
- Adjust meal generation based on:
  - Skips
  - Repeats
- Add simple weighting system

#### Phase 6 — Polish (Day 23–28)
- Improve loading states
- Add empty state handling
- Refine UI for calm experience
- Fix bugs

---

### Timeline with checkpoints

- Week 1 → Backend + database ready
- Week 2 → Meal generation working
- Week 3 → UI + grocery list complete
- Week 4 → Feedback loop + polish

---

### Team roles & rituals

- **Product (you):**
  - Define features
  - Validate UX decisions

- **Engineer:**
  - Build backend + frontend
  - Integrate AI

- **Designer (optional):**
  - Ensure calm, minimal UX

- **Rituals:**
  - Weekly build review
  - Monthly 30-min usability test (3 users)
  - Track top 3 confusions → fix first

---

### Optional integrations & stretch goals

- Grocery delivery APIs (Instacart, Amazon Fresh)
- Calendar integration (detect busy days)
- Voice assistant support
- Recipe APIs for richer meal data
