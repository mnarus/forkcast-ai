from apps.planned_meal.models import PlannedMeal


CATEGORY_KEYWORDS = {
    "produce": [
        "apple",
        "arugula",
        "avocado",
        "banana",
        "basil",
        "bell pepper",
        "berries",
        "broccoli",
        "cabbage",
        "carrot",
        "cauliflower",
        "celery",
        "cilantro",
        "corn",
        "cucumber",
        "garlic",
        "ginger",
        "greens",
        "jalapeno",
        "kale",
        "lemon",
        "lettuce",
        "lime",
        "mango",
        "mushroom",
        "onion",
        "parsley",
        "peas",
        "pepper",
        "pineapple",
        "potato",
        "romaine",
        "salad",
        "shallot",
        "snap pea",
        "spinach",
        "squash",
        "tomato",
        "zucchini",
    ],
    "dairy": [
        "butter",
        "cheddar",
        "cheese",
        "cream",
        "feta",
        "greek yogurt",
        "milk",
        "mozzarella",
        "parmesan",
        "ricotta",
        "sour cream",
        "yogurt",
    ],
    "protein": [
        "beef",
        "chicken",
        "chickpea",
        "egg",
        "ground turkey",
        "lentil",
        "pork",
        "salmon",
        "sausage",
        "shrimp",
        "steak",
        "tempeh",
        "tofu",
        "tuna",
        "turkey",
    ],
    "grains": [
        "bread",
        "bun",
        "couscous",
        "farro",
        "flour",
        "noodle",
        "oat",
        "orzo",
        "pasta",
        "quinoa",
        "rice",
        "tortilla",
    ],
    "canned_jarred": [
        "beans",
        "broth",
        "coconut milk",
        "marinara",
        "olive",
        "pesto",
        "salsa",
        "sauce",
        "stock",
        "tomato paste",
    ],
    "spices_oils": [
        "cumin",
        "curry",
        "honey",
        "oil",
        "paprika",
        "pepper flakes",
        "salt",
        "seasoning",
        "soy sauce",
        "vinegar",
    ],
    "frozen": [
        "frozen",
    ],
}

CATEGORY_LABELS = {
    "produce": "Produce",
    "dairy": "Dairy",
    "protein": "Protein",
    "grains": "Grains & Bakery",
    "canned_jarred": "Canned & Jarred",
    "spices_oils": "Spices, Sauces & Oils",
    "frozen": "Frozen",
    "other": "Other",
}


def normalize_ingredient_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def categorize_ingredient(ingredient):
    normalized = ingredient.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                return category

    return "other"


def build_grocery_items_from_ingredients(ingredients):
    items = []
    seen_items = set()

    for ingredient in ingredients:
        key = ingredient.lower()
        if key in seen_items:
            continue
        seen_items.add(key)
        items.append(ingredient)

    return items


def build_grouped_grocery_items(items):
    grouped = {key: [] for key in CATEGORY_LABELS}

    for ingredient in items:
        grouped[categorize_ingredient(ingredient)].append(ingredient)

    return [
        {
            "category": category,
            "label": CATEGORY_LABELS[category],
            "items": sorted(grouped_items, key=str.lower),
        }
        for category, grouped_items in grouped.items()
        if grouped_items
    ]


def build_grocery_payload(items):
    deduped_items = build_grocery_items_from_ingredients(items)
    return {
        "items": deduped_items,
        "grouped_items": build_grouped_grocery_items(deduped_items),
    }


def build_grocery_payload_from_generated_meals(generated_meals):
    ingredients = []

    for meal in generated_meals:
        ingredients.extend(normalize_ingredient_list(meal.get("ingredients")))

    return build_grocery_payload(ingredients)


def build_grocery_payload_from_planned_meals(planned_meals):
    ingredients = []

    for planned_meal in planned_meals:
        if planned_meal.meal:
            ingredients.extend(normalize_ingredient_list(planned_meal.meal.ingredients))

    return build_grocery_payload(ingredients)


def build_grocery_payload_for_plan(weekly_plan):
    planned_meals = PlannedMeal.objects.filter(weekly_plan=weekly_plan).select_related("meal")
    return build_grocery_payload_from_planned_meals(planned_meals)
