"""Expense category analyzer tool for MCP server."""

from mcp.types import ToolAnnotations

from core.server import mcp


@mcp.tool(
    annotations=ToolAnnotations(
        title="Analyze Expenses",
        readOnlyHint=True,
    ),
)
def analyze_expenses(
    housing: float,
    food: float,
    transport: float,
    subscriptions: float,
    entertainment: float,
    other: float,
) -> dict:
    """Analyze expense categories and identify spending concentration.

    Args:
        housing: Housing/rent expenses.
        food: Food expenses.
        transport: Transport expenses.
        subscriptions: Subscription expenses.
        entertainment: Entertainment expenses.
        other: Other expenses.

    Returns:
        Expense breakdown and largest category.
    """
    categories = {
        "housing": housing,
        "food": food,
        "transport": transport,
        "subscriptions": subscriptions,
        "entertainment": entertainment,
        "other": other,
    }

    total = sum(categories.values())

    if total <= 0:
        return {
            "total_expenses": 0,
            "largest_category": None,
            "breakdown_percent": {},
            "warning": "Total expenses must be greater than zero.",
        }

    largest_category = max(categories, key=categories.get)
    largest_amount = categories[largest_category]

    breakdown = {
        name: round(amount / total * 100, 2)
        for name, amount in categories.items()
    }

    warning = None
    if breakdown[largest_category] >= 50:
        warning = (
            f"{largest_category} is {breakdown[largest_category]}% of total expenses. "
            "This category dominates the budget."
        )

    return {
        "total_expenses": round(total, 2),
        "largest_category": largest_category,
        "largest_amount": round(largest_amount, 2),
        "breakdown_percent": breakdown,
        "warning": warning,
    }