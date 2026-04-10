import json
from openai import OpenAI

client = OpenAI()


def generate_weekly_meal_plan(preferences, dislikes, dietary_tags, recent_meals, schedule):
    prompt_template = open(
        "apps/weekly_plan/prompts/meal_plan_prompt.txt"
    ).read()

    prompt = prompt_template.format(
        preferences=preferences,
        dislikes=dislikes,
        dietary_tags=dietary_tags,
        recent_meals=recent_meals,
        schedule=schedule,
    )

    response = client.chat.completions.create(
        model="gpt-4.1-mini",  # fast + cheap, good enough for this
        messages=[
            {"role": "system", "content": "You generate structured meal plans."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )

    content = response.choices[0].message.content

    try:
        meals = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("LLM returned invalid JSON")

    return meals