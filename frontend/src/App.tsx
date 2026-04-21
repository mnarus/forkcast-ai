import { useEffect, useState } from 'react'
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

type PlannedMeal = {
  id: number
  day_of_week: string
  notes: string
  meal: Meal | null
}

type GroceryGroup = {
  category: string
  label: string
  items: string[]
}

type PlanResponse = {
  id: number
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

type PlannerForm = {
  preferences: string
  dislikes: string
  dietaryTags: string
  notes: string
  maxPrepTimeMinutes: string
}

const DEMO_USER_KEY = 'forkcast-demo-user-id'

const initialForm: PlannerForm = {
  preferences: 'high protein, easy cleanup',
  dislikes: 'mushrooms',
  dietaryTags: 'pescatarian-flexible',
  notes: 'Keep dinners realistic for busy weeknights.',
  maxPrepTimeMinutes: '30',
}

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

function App() {
  const [form, setForm] = useState<PlannerForm>(initialForm)
  const [userId, setUserId] = useState<number | null>(null)
  const [plan, setPlan] = useState<PlanResponse | null>(null)
  const [groceryList, setGroceryList] = useState<GroceryListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

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

  async function loadGroceryList(planId: number) {
    const response = await fetch(`/api/plans/${planId}/grocery-list/`)

    if (!response.ok) {
      throw new Error(`Unable to load grocery list (${response.status})`)
    }

    const data: GroceryListResponse = await response.json()
    setGroceryList(data)
  }

  async function handleGeneratePlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!userId) {
      setError('Planner is still setting up. Try again in a moment.')
      return
    }

    setSubmitting(true)
    setError('')

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
        throw new Error(data && 'error' in data ? data.error || 'Unable to generate plan' : 'Unable to generate plan')
      }

      const nextPlan = data as PlanResponse
      setPlan(nextPlan)
      await loadGroceryList(nextPlan.id)
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

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Forkcast AI</p>
          <h1>Weekly dinners and your grocery run, tied together.</h1>
          <p className="hero-text">
            Generate a realistic weeknight plan, then shop from an ingredient list that is automatically grouped for the store.
          </p>
        </div>

        <form className="planner-card" onSubmit={handleGeneratePlan}>
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

          <p className="status-text">
            {error
              ? error
              : loading
                ? 'Setting up a demo planner profile...'
                : 'Ready to build this week.'}
          </p>
        </form>
      </section>

      <section className="content-grid">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="section-label">Weekly Plan</p>
              <h2>Meals for the week</h2>
            </div>
            {plan ? <span className="week-pill">{plan.week_start_date}</span> : null}
          </div>

          {plan ? (
            <div className="meal-list">
              {plan.meals.map((plannedMeal) => (
                <article className="meal-card" key={plannedMeal.id}>
                  <div className="meal-topline">
                    <span className="meal-day">{plannedMeal.day_of_week}</span>
                    <span className="meal-meta">
                      {plannedMeal.meal?.prep_time_minutes ?? '--'} min •{' '}
                      {formatDifficulty(plannedMeal.meal?.difficulty ?? '')}
                    </span>
                  </div>
                  <h3>{plannedMeal.meal?.name ?? 'Meal unavailable'}</h3>
                  <p>{plannedMeal.meal?.description || plannedMeal.notes || 'No notes yet.'}</p>
                  <div className="ingredient-chips">
                    {(plannedMeal.meal?.ingredients ?? []).map((ingredient) => (
                      <span className="chip" key={`${plannedMeal.id}-${ingredient}`}>
                        {ingredient}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>Your generated dinners will land here.</p>
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="section-label">Grocery List</p>
              <h2>Grouped for the store</h2>
            </div>
            {groceryList ? (
              <span className="week-pill">{groceryList.items.length} items</span>
            ) : null}
          </div>

          {groceryList ? (
            <div className="grocery-groups">
              {groceryList.grouped_items.map((group) => (
                <section className="grocery-group" key={group.category}>
                  <div className="grocery-group-header">
                    <h3>{group.label}</h3>
                    <span>{group.items.length}</span>
                  </div>
                  <ul>
                    {group.items.map((item) => (
                      <li key={`${group.category}-${item}`}>{item}</li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>Generate a plan to build your grocery list.</p>
            </div>
          )}
        </article>
      </section>
    </main>
  )
}

export default App
