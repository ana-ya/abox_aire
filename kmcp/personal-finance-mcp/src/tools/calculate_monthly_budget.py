"""Monthly budget calculator tool for MCP server."""

from mcp.types import ToolAnnotations

from core.server import mcp


@mcp.tool(
    annotations=ToolAnnotations(
        title="Calculate Monthly Budget",
        readOnlyHint=True,
    ),
)
def calculate_monthly_budget(
    income: float,
    rent: float,
    food: float,
    transport: float,
    subscriptions: float,
    savings_goal: float,
) -> dict:
    """Calculate a monthly budget summary.

    Args:
        income: Monthly income.
        rent: Monthly rent or housing cost.
        food: Monthly food spending.
        transport: Monthly transport spending.
        subscriptions: Monthly subscriptions spending.
        savings_goal: Desired monthly savings.

    Returns:
        Budget summary with expenses, remaining money, savings rate, and recommendation.
    """
    fixed_expenses = rent + food + transport + subscriptions
    remaining_after_expenses = income - fixed_expenses
    remaining_after_savings = remaining_after_expenses - savings_goal
    savings_rate = (savings_goal / income * 100) if income > 0 else 0

    if income <= 0:
        recommendation = "Income must be greater than zero."
    elif remaining_after_savings >= 0:
        recommendation = "Budget is feasible. Savings goal can be reached."
    else:
        gap = abs(remaining_after_savings)
        recommendation = (
            f"Budget is short by {gap:.2f}. Reduce expenses or lower the savings goal."
        )

    return {
        "income": round(income, 2),
        "fixed_expenses": round(fixed_expenses, 2),
        "remaining_after_expenses": round(remaining_after_expenses, 2),
        "savings_goal": round(savings_goal, 2),
        "remaining_after_savings": round(remaining_after_savings, 2),
        "savings_rate_percent": round(savings_rate, 2),
        "recommendation": recommendation,
    }