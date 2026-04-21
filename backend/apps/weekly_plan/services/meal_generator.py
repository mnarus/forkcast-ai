import json
from pathlib import Path

from django.conf import settings
from openai import OpenAI


PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "meal_plan_prompt.txt"
DEFAULT_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def _normalize_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _load_prompt_template():
    return PROMPT_PATH.read_text(encoding="utf-8")


def _validate_generated_meals(meals, *, dinner_count, max_prep_time_minutes, dislikes):
    if not isinstance(meals, list):
        raise ValueError("LLM returned an invalid meal plan payload")

    if len(meals) != dinner_count:
        raise ValueError(f"LLM returned {len(meals)} meals, expected {dinner_count}")

    seen_days = set()
    seen_meals = set()
    dislike_terms = {term.lower() for term in dislikes}
    normalized_meals = []

    for index, meal in enumerate(meals):
        if not isinstance(meal, dict):
            raise ValueError(f"Meal {index + 1} is not an object")

        day = str(meal.get("day") or "").strip()
        meal_name = str(meal.get("meal") or "").strip()
        description = str(meal.get("description") or "").strip()
        difficulty = str(meal.get("difficulty") or "").strip().lower()
        ingredients = _normalize_list(meal.get("ingredients"))

        try:
            prep_time = int(meal.get("time"))
        except (TypeError, ValueError):
            raise ValueError(f"Meal {meal_name or index + 1} is missing a valid prep time")

        if day not in DEFAULT_DAYS:
            raise ValueError(f"Meal {meal_name or index + 1} uses an unsupported day: {day}")
        if day in seen_days:
            raise ValueError(f"Duplicate day found in generated plan: {day}")
        if not meal_name:
            raise ValueError(f"Meal {index + 1} is missing a name")
        if meal_name.lower() in seen_meals:
            raise ValueError(f"Duplicate meal found in generated plan: {meal_name}")
        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError(f"Meal {meal_name} has invalid difficulty: {difficulty}")
        if prep_time <= 0 or prep_time > max_prep_time_minutes:
            raise ValueError(
                f"Meal {meal_name} exceeds the prep time limit of {max_prep_time_minutes} minutes"
            )
        if not ingredients:
            raise ValueError(f"Meal {meal_name} must include at least one ingredient")

        searchable_text = " ".join([meal_name, description, *ingredients]).lower()
        conflicting_dislikes = [term for term in dislike_terms if term and term in searchable_text]
        if conflicting_dislikes:
            raise ValueError(
                f"Meal {meal_name} conflicts with dislikes: {', '.join(sorted(conflicting_dislikes))}"
            )

        seen_days.add(day)
        seen_meals.add(meal_name.lower())
        normalized_meals.append(
            {
                "day": day,
                "meal": meal_name,
                "description": description,
                "difficulty": difficulty,
                "time": prep_time,
                "ingredients": ingredients,
            }
        )

    return normalized_meals


def generate_weekly_meal_plan(
    preferences,
    dislikes,
    dietary_tags,
    recent_meals,
    schedule,
    *,
    max_prep_time_minutes=30,
    dinner_count=5,
):
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    prompt_template = _load_prompt_template()
    prompt = prompt_template.format(
        dinner_count=dinner_count,
        max_prep_time_minutes=max_prep_time_minutes,
        preferences=json.dumps(_normalize_list(preferences)),
        dislikes=json.dumps(_normalize_list(dislikes)),
        dietary_tags=json.dumps(_normalize_list(dietary_tags)),
        recent_meals=json.dumps(_normalize_list(recent_meals)),
        schedule=json.dumps(schedule or {}, indent=2),
    )

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate calm, practical weekly dinner plans as strict JSON only. "
                    "Do not include markdown fences or extra commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )

    content = response.choices[0].message.content

    try:
        meals = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM returned invalid JSON") from exc

    return _validate_generated_meals(
        meals,
        dinner_count=dinner_count,
        max_prep_time_minutes=max_prep_time_minutes,
        dislikes=_normalize_list(dislikes),
    )
