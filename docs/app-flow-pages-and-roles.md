## app-flow-pages-and-roles.md

### Site map (top-level pages only)
- Home (Weekly Plan)
- Meal Detail
- Grocery List
- Preferences
- Onboarding

---

### Purpose of each page

- **Home (Weekly Plan)**
  - View weekly dinners and take quick actions

- **Meal Detail**
  - See recipe, ingredients, and context (“why this meal”)

- **Grocery List**
  - View and check off aggregated ingredients

- **Preferences**
  - Manage dietary needs, dislikes, and basic settings

- **Onboarding**
  - Capture initial preferences and set tone

---

### User roles and access levels

- **Primary User**
  - Full access to plans, preferences, and actions

- **Household Member (future)**
  - View plans
  - Mark meals as cooked/skipped

- **Admin (internal)**
  - Manage system, debug issues

---

### Primary user journeys (3 steps max each)

**1. Weekly planning (default flow)**
- Open app
- View generated weekly plan
- Accept or swap meals

**2. Cooking a meal**
- Open today’s meal
- Tap “Cook this”
- Meal logged automatically

**3. Skipping a meal**
- Open meal
- Tap “Skip”
- System adapts future plans

**4. Grocery run**
- Open grocery list
- Check off items while shopping
- Complete list

**5. First-time onboarding**
- Answer 3–5 simple questions
- System generates first plan
- Land on Home screen

---

### Flow principles

- Default first → no blank states
- One decision per screen
- Actions are obvious (Cook / Skip / Swap)
- System does the thinking, user confirms

