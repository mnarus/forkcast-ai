import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type Meal = {
  id: number
  name: string
  description: string
  ingredients: string[]
  prep_time_minutes: number | null
  difficulty: string
}

type MealFeedback = {
  id: number
  status: 'cooked' | 'skipped'
  liked: boolean | null
  note: string
  created_at: string
}

type PlannedMeal = {
  id: number
  day_of_week: string
  notes: string
  meal: Meal | null
  latest_feedback: MealFeedback | null
}

type GroceryGroup = {
  category: string
  label: string
  items: string[]
}

type PlanResponse = {
  id: number
  user_id: number
  week_start_date: string
  notes: string
  meals: PlannedMeal[]
  grocery_list: string[]
  grocery_list_grouped: GroceryGroup[]
}

type GroceryListResponse = {
  plan_id: number
  week_start_date: string
  items: string[]
  grouped_items: GroceryGroup[]
}

type BehaviorResponse = MealFeedback & {
  planned_meal_id: number
}

type SwapResponse = {
  planned_meal: PlannedMeal
  grocery_list: GroceryListResponse
}

type PlannerForm = {
  preferences: string
  dislikes: string
  dietaryTags: string
  notes: string
  maxPrepTimeMinutes: string
}

type Screen = 'weekly' | 'detail' | 'grocery'

const DEMO_USER_KEY = 'forkcast-demo-user-id'

const initialForm: PlannerForm = {
  preferences: 'high protein, easy cleanup',
  dislikes: 'mushrooms',
  dietaryTags: 'pescatarian-flexible',
  notes: 'Keep dinners realistic for busy weeknights.',
  maxPrepTimeMinutes: '30',
}

const screenOptions: Array<{ id: Screen; label: string }> = [
  { id: 'weekly', label: 'Weekly plan' },
  { id: 'detail', label: 'Meal detail' },
  { id: 'grocery', label: 'Grocery list' },
]

function splitCommaSeparated(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function formatDifficulty(value: string) {
  if (!value) {
    return 'Flexible'
  }

  return value.charAt(0).toUpperCase() + value.slice(1)
}

function formatStatus(status: PlannedMeal['latest_feedback'] | null) {
  if (!status) {
    return 'Planned'
  }

  return status.status === 'cooked' ? 'Cooked' : 'Skipped'
}

function App() {
  const [form, setForm] = useState<PlannerForm>(initialForm)
  const [userId, setUserId] = useState<number | null>(null)
  const [plan, setPlan] = useState<PlanResponse | null>(null)
  const [groceryList, setGroceryList] = useState<GroceryListResponse | null>(null)
  const [checkedItems, setCheckedItems] = useState<string[]>([])
  const [selectedMealId, setSelectedMealId] = useState<number | null>(null)
  const [activeScreen, setActiveScreen] = useState<Screen>('weekly')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [actionMealId, setActionMealId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('Ready to build this week.')

  const selectedMeal = useMemo(
    () => plan?.meals.find((plannedMeal) => plannedMeal.id === selectedMealId) ?? null,
    [plan, selectedMealId],
  )

  useEffect(() => {
    let ignore = false

    async function ensureDemoUser() {
      setLoading(true)

      try {
        const existingUserId = window.localStorage.getItem(DEMO_USER_KEY)

        if (existingUserId) {
          if (!ignore) {
            setUserId(Number(existingUserId))
            setError('')
            setNotice('Ready to build this week.')
          }
          return
        }

        const timestamp = Date.now()
        const response = await fetch('/api/users/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: `demo-${timestamp}`,
            password: `demo-${timestamp}-pw`,
            email: `demo-${timestamp}@forkcast.local`,
          }),
        })

        if (!response.ok) {
          throw new Error(`Unable to create demo user (${response.status})`)
        }

        const data: { id: number } = await response.json()
        window.localStorage.setItem(DEMO_USER_KEY, String(data.id))

        if (!ignore) {
          setUserId(data.id)
          setError('')
          setNotice('Ready to build this week.')
        }
      } catch (loadError) {
        if (!ignore) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : 'Unable to initialize planner',
          )
        }
      } finally {
        if (!ignore) {
          setLoading(false)
        }
      }
    }

    void ensureDemoUser()

    return () => {
      ignore = true
    }
  }, [])

  useEffect(() => {
    if (!plan?.meals.length) {
      setSelectedMealId(null)
      return
    }

    setSelectedMealId((current) => {
      if (current && plan.meals.some((meal) => meal.id === current)) {
        return current
      }

      return plan.meals[0].id
    })
  }, [plan])

  useEffect(() => {
    if (!groceryList) {
      setCheckedItems([])
      return
    }

    setCheckedItems((current) => current.filter((item) => groceryList.items.includes(item)))
  }, [groceryList])

  async function loadGroceryList(planId: number) {
    const response = await fetch(`/api/plans/${planId}/grocery-list/`)

    if (!response.ok) {
      throw new Error(`Unable to load grocery list (${response.status})`)
    }

    const data: GroceryListResponse = await response.json()
    setGroceryList(data)
  }

  function updatePlannedMeal(nextMeal: PlannedMeal) {
    setPlan((currentPlan) => {
      if (!currentPlan) {
        return currentPlan
      }

      return {
        ...currentPlan,
        meals: currentPlan.meals.map((plannedMeal) =>
          plannedMeal.id === nextMeal.id ? nextMeal : plannedMeal,
        ),
      }
    })
  }

  async function handleGeneratePlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!userId) {
      setError('Planner is still setting up. Try again in a moment.')
      return
    }

    setSubmitting(true)
    setError('')
    setNotice('Building a calm weeknight plan...')

    try {
      const response = await fetch('/api/plans/generate/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          preferences: splitCommaSeparated(form.preferences),
          dislikes: splitCommaSeparated(form.dislikes),
          dietary_tags: splitCommaSeparated(form.dietaryTags),
          notes: form.notes.trim(),
          max_prep_time_minutes: Number(form.maxPrepTimeMinutes),
        }),
      })

      const data = (await response.json()) as PlanResponse | { error?: string }

      if (!response.ok) {
        throw new Error(
          data && 'error' in data ? data.error || 'Unable to generate plan' : 'Unable to generate plan',
        )
      }

      const nextPlan = data as PlanResponse
      setPlan(nextPlan)
      await loadGroceryList(nextPlan.id)
      setActiveScreen('weekly')
      setNotice("You're all set for the week.")
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : 'Unable to generate plan',
      )
    } finally {
      setSubmitting(false)
    }
  }

  async function handleBehaviorAction(plannedMeal: PlannedMeal, status: 'cooked' | 'skipped') {
    setActionMealId(plannedMeal.id)
    setError('')

    try {
      const response = await fetch('/api/behavior-logs/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          planned_meal_id: plannedMeal.id,
          status,
        }),
      })

      const data = (await response.json()) as BehaviorResponse | { error?: string }

      if (!response.ok) {
        throw new Error(data && 'error' in data ? data.error || 'Unable to save action' : 'Unable to save action')
      }

      const behavior = data as BehaviorResponse
      updatePlannedMeal({
        ...plannedMeal,
        latest_feedback: {
          id: behavior.id,
          status: behavior.status,
          liked: behavior.liked,
          note: behavior.note,
          created_at: behavior.created_at,
        },
      })
      setNotice(status === 'cooked' ? 'Nice. Meal marked as cooked.' : 'Meal skipped. We can adjust from here.')
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Unable to save action')
    } finally {
      setActionMealId(null)
    }
  }

  async function handleSwap(plannedMeal: PlannedMeal) {
    setActionMealId(plannedMeal.id)
    setError('')

    try {
      const response = await fetch(`/api/planned-meals/${plannedMeal.id}/swap/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferences: splitCommaSeparated(form.preferences),
          dislikes: splitCommaSeparated(form.dislikes),
          dietary_tags: splitCommaSeparated(form.dietaryTags),
          notes: form.notes.trim(),
          max_prep_time_minutes: Number(form.maxPrepTimeMinutes),
        }),
      })

      const data = (await response.json()) as SwapResponse | { error?: string }

      if (!response.ok) {
        throw new Error(data && 'error' in data ? data.error || 'Unable to swap meal' : 'Unable to swap meal')
      }

      const swapData = data as SwapResponse
      updatePlannedMeal(swapData.planned_meal)
      setGroceryList(swapData.grocery_list)
      setActiveScreen('detail')
      setSelectedMealId(swapData.planned_meal.id)
      setNotice(`Swapped in ${swapData.planned_meal.meal?.name ?? 'a new meal'}.`)
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Unable to swap meal')
    } finally {
      setActionMealId(null)
    }
  }

  function toggleItem(item: string) {
    setCheckedItems((current) =>
      current.includes(item)
        ? current.filter((entry) => entry !== item)
        : [...current, item],
    )
  }

  const groceryCompletion = groceryList?.items.length
    ? Math.round((checkedItems.length / groceryList.items.length) * 100)
    : 0

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Forkcast AI</p>
          <h1>Dinner planning with less friction and more follow-through.</h1>
          <p className="hero-text">
            Build a weekly plan, open any meal for context, and keep your grocery list aligned as you cook, skip, or swap.
          </p>

          <div className="hero-stats" aria-label="Planner summary">
            <article className="stat-card">
              <span className="stat-value">{plan?.meals.length ?? 0}</span>
              <span className="stat-label">Meals planned</span>
            </article>
            <article className="stat-card">
              <span className="stat-value">
                {plan?.meals.filter((meal) => meal.latest_feedback?.status === 'cooked').length ?? 0}
              </span>
              <span className="stat-label">Cooked</span>
            </article>
            <article className="stat-card">
              <span className="stat-value">{groceryList?.items.length ?? 0}</span>
              <span className="stat-label">Grocery items</span>
            </article>
          </div>
        </div>

        <form className="planner-card" onSubmit={handleGeneratePlan}>
          <div className="panel-heading planner-heading">
            <div>
              <p className="section-label">Planner setup</p>
              <h2>Generate this week</h2>
            </div>
            <span className="week-pill">{loading ? 'Setting up' : 'Demo mode'}</span>
          </div>

          <div className="field-grid">
            <label className="field">
              <span>Preferences</span>
              <input
                value={form.preferences}
                onChange={(event) =>
                  setForm((current) => ({ ...current, preferences: event.target.value }))
                }
                placeholder="high protein, family friendly"
              />
            </label>

            <label className="field">
              <span>Dislikes</span>
              <input
                value={form.dislikes}
                onChange={(event) =>
                  setForm((current) => ({ ...current, dislikes: event.target.value }))
                }
                placeholder="mushrooms, olives"
              />
            </label>

            <label className="field">
              <span>Dietary tags</span>
              <input
                value={form.dietaryTags}
                onChange={(event) =>
                  setForm((current) => ({ ...current, dietaryTags: event.target.value }))
                }
                placeholder="vegetarian, dairy free"
              />
            </label>

            <label className="field">
              <span>Max prep time</span>
              <input
                type="number"
                min="10"
                max="120"
                value={form.maxPrepTimeMinutes}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    maxPrepTimeMinutes: event.target.value,
                  }))
                }
              />
            </label>
          </div>

          <label className="field field-notes">
            <span>Notes for this week</span>
            <textarea
              rows={3}
              value={form.notes}
              onChange={(event) =>
                setForm((current) => ({ ...current, notes: event.target.value }))
              }
              placeholder="Need extra simple meals on Tuesday and Thursday."
            />
          </label>

          <button className="generate-button" disabled={loading || submitting} type="submit">
            {submitting ? 'Generating plan...' : 'Generate weekly plan'}
          </button>

          <p className={`status-text ${error ? 'status-error' : ''}`}>
            {error
              ? error
              : loading
                ? 'Setting up a demo planner profile...'
                : notice}
          </p>
        </form>
      </section>

      <section className="workspace-panel">
        <div className="workspace-header">
          <div>
            <p className="section-label">Phase 4 UI</p>
            <h2>Weekly plan, meal detail, and grocery list</h2>
          </div>
          {plan ? <span className="week-pill">Week of {plan.week_start_date}</span> : null}
        </div>

        <div className="screen-tabs" role="tablist" aria-label="Planner views">
          {screenOptions.map((screen) => (
            <button
              key={screen.id}
              className={`screen-tab ${activeScreen === screen.id ? 'is-active' : ''}`}
              onClick={() => setActiveScreen(screen.id)}
              role="tab"
              type="button"
              aria-selected={activeScreen === screen.id}
            >
              {screen.label}
            </button>
          ))}
        </div>

        {activeScreen === 'weekly' ? (
          <section className="screen-panel">
            <div className="screen-heading">
              <div>
                <p className="section-label">Weekly plan view</p>
                <h3>Meals for the week</h3>
              </div>
              {plan ? <span className="helper-copy">Tap a meal to open detail.</span> : null}
            </div>

            {plan ? (
              <div className="meal-list">
                {plan.meals.map((plannedMeal) => {
                  const isBusy = actionMealId === plannedMeal.id
                  const isSelected = selectedMealId === plannedMeal.id

                  return (
                    <article
                      className={`meal-card ${isSelected ? 'is-selected' : ''}`}
                      key={plannedMeal.id}
                    >
                      <button
                        className="meal-card-button"
                        onClick={() => {
                          setSelectedMealId(plannedMeal.id)
                          setActiveScreen('detail')
                        }}
                        type="button"
                      >
                        <div className="meal-topline">
                          <span className="meal-day">{plannedMeal.day_of_week}</span>
                          <span className={`meal-status status-${plannedMeal.latest_feedback?.status ?? 'planned'}`}>
                            {formatStatus(plannedMeal.latest_feedback)}
                          </span>
                        </div>
                        <h3>{plannedMeal.meal?.name ?? 'Meal unavailable'}</h3>
                        <p>
                          {plannedMeal.meal?.description || plannedMeal.notes || 'No notes yet.'}
                        </p>
                        <div className="meal-meta-row">
                          <span className="meal-meta">
                            {plannedMeal.meal?.prep_time_minutes ?? '--'} min
                          </span>
                          <span className="meal-meta">
                            {formatDifficulty(plannedMeal.meal?.difficulty ?? '')}
                          </span>
                        </div>
                        <div className="ingredient-chips">
                          {(plannedMeal.meal?.ingredients ?? []).slice(0, 5).map((ingredient) => (
                            <span className="chip" key={`${plannedMeal.id}-${ingredient}`}>
                              {ingredient}
                            </span>
                          ))}
                        </div>
                      </button>

                      <div className="meal-actions">
                        <button
                          className="action-button action-primary"
                          disabled={isBusy}
                          onClick={() => void handleBehaviorAction(plannedMeal, 'cooked')}
                          type="button"
                        >
                          {isBusy ? 'Saving...' : 'Cook'}
                        </button>
                        <button
                          className="action-button"
                          disabled={isBusy}
                          onClick={() => void handleBehaviorAction(plannedMeal, 'skipped')}
                          type="button"
                        >
                          Skip
                        </button>
                        <button
                          className="action-button"
                          disabled={isBusy}
                          onClick={() => void handleSwap(plannedMeal)}
                          type="button"
                        >
                          Swap
                        </button>
                      </div>
                    </article>
                  )
                })}
              </div>
            ) : (
              <div className="empty-state">
                <p>Your generated dinners will land here.</p>
              </div>
            )}
          </section>
        ) : null}

        {activeScreen === 'detail' ? (
          <section className="screen-panel">
            <div className="screen-heading">
              <div>
                <p className="section-label">Meal detail</p>
                <h3>{selectedMeal?.meal?.name ?? 'Pick a meal to inspect'}</h3>
              </div>
              {selectedMeal ? (
                <span className={`meal-status status-${selectedMeal.latest_feedback?.status ?? 'planned'}`}>
                  {formatStatus(selectedMeal.latest_feedback)}
                </span>
              ) : null}
            </div>

            {selectedMeal ? (
              <div className="detail-layout">
                <article className="detail-card detail-main">
                  <div className="detail-topline">
                    <span className="meal-day">{selectedMeal.day_of_week}</span>
                    <div className="detail-metas">
                      <span className="meal-meta">
                        {selectedMeal.meal?.prep_time_minutes ?? '--'} min
                      </span>
                      <span className="meal-meta">
                        {formatDifficulty(selectedMeal.meal?.difficulty ?? '')}
                      </span>
                    </div>
                  </div>
                  <p className="detail-description">
                    {selectedMeal.meal?.description || selectedMeal.notes || 'No notes yet.'}
                  </p>

                  <div className="detail-section">
                    <h4>Ingredients</h4>
                    <ul className="detail-list">
                      {(selectedMeal.meal?.ingredients ?? []).map((ingredient) => (
                        <li key={`${selectedMeal.id}-${ingredient}`}>{ingredient}</li>
                      ))}
                    </ul>
                  </div>
                </article>

                <aside className="detail-card detail-sidebar">
                  <div className="detail-section">
                    <h4>Context</h4>
                    <p>{selectedMeal.notes || plan?.notes || 'Built to fit the current week.'}</p>
                  </div>

                  <div className="detail-section">
                    <h4>Actions</h4>
                    <div className="detail-actions">
                      <button
                        className="action-button action-primary"
                        disabled={actionMealId === selectedMeal.id}
                        onClick={() => void handleBehaviorAction(selectedMeal, 'cooked')}
                        type="button"
                      >
                        {actionMealId === selectedMeal.id ? 'Saving...' : 'Cook'}
                      </button>
                      <button
                        className="action-button"
                        disabled={actionMealId === selectedMeal.id}
                        onClick={() => void handleBehaviorAction(selectedMeal, 'skipped')}
                        type="button"
                      >
                        Skip
                      </button>
                      <button
                        className="action-button"
                        disabled={actionMealId === selectedMeal.id}
                        onClick={() => void handleSwap(selectedMeal)}
                        type="button"
                      >
                        Swap
                      </button>
                    </div>
                  </div>

                  <div className="detail-section">
                    <h4>Latest update</h4>
                    <p>
                      {selectedMeal.latest_feedback
                        ? `${formatStatus(selectedMeal.latest_feedback)} on ${new Date(selectedMeal.latest_feedback.created_at).toLocaleDateString()}`
                        : 'No action logged yet.'}
                    </p>
                  </div>
                </aside>
              </div>
            ) : (
              <div className="empty-state">
                <p>Select a meal from the weekly plan to open its details.</p>
              </div>
            )}
          </section>
        ) : null}

        {activeScreen === 'grocery' ? (
          <section className="screen-panel">
            <div className="screen-heading">
              <div>
                <p className="section-label">Grocery list</p>
                <h3>Grouped for the store</h3>
              </div>
              {groceryList ? (
                <span className="week-pill">{groceryCompletion}% checked</span>
              ) : null}
            </div>

            {groceryList ? (
              <div className="grocery-layout">
                <article className="grocery-summary">
                  <h4>Shopping progress</h4>
                  <div className="progress-track" aria-hidden="true">
                    <div className="progress-fill" style={{ width: `${groceryCompletion}%` }} />
                  </div>
                  <p>
                    {checkedItems.length} of {groceryList.items.length} items checked off.
                  </p>
                </article>

                <div className="grocery-groups">
                  {groceryList.grouped_items.map((group) => (
                    <section className="grocery-group" key={group.category}>
                      <div className="grocery-group-header">
                        <h4>{group.label}</h4>
                        <span>{group.items.length}</span>
                      </div>
                      <ul className="grocery-checklist">
                        {group.items.map((item) => {
                          const checked = checkedItems.includes(item)

                          return (
                            <li key={`${group.category}-${item}`}>
                              <label className={`check-row ${checked ? 'is-checked' : ''}`}>
                                <input
                                  checked={checked}
                                  onChange={() => toggleItem(item)}
                                  type="checkbox"
                                />
                                <span>{item}</span>
                              </label>
                            </li>
                          )
                        })}
                      </ul>
                    </section>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <p>Generate a plan to build your grocery list.</p>
              </div>
            )}
          </section>
        ) : null}
      </section>
    </main>
  )
}

export default App
