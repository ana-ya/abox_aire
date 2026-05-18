"""Debt payoff estimator tool for MCP server."""

import math

from mcp.types import ToolAnnotations

from core.server import mcp


@mcp.tool(
    annotations=ToolAnnotations(
        title="Debt Payoff Estimate",
        readOnlyHint=True,
    ),
)
def debt_payoff_estimate(
    debt_amount: float,
    annual_interest_rate_percent: float,
    monthly_payment: float,
) -> dict:
    """Estimate how long it takes to pay off debt.

    Args:
        debt_amount: Current debt balance.
        annual_interest_rate_percent: APR as percentage.
        monthly_payment: Monthly payment amount.

    Returns:
        Estimated payoff months, total paid, and total interest.
    """
    if debt_amount <= 0:
        return {"error": "Debt amount must be greater than zero."}

    if monthly_payment <= 0:
        return {"error": "Monthly payment must be greater than zero."}

    monthly_rate = annual_interest_rate_percent / 100 / 12

    if monthly_rate == 0:
        months = math.ceil(debt_amount / monthly_payment)
        total_paid = months * monthly_payment
        return {
            "months": months,
            "years": round(months / 12, 2),
            "total_paid": round(total_paid, 2),
            "total_interest": round(total_paid - debt_amount, 2),
            "warning": None,
        }

    monthly_interest = debt_amount * monthly_rate
    if monthly_payment <= monthly_interest:
        return {
            "error": "Monthly payment is too low to reduce the debt balance.",
            "monthly_interest": round(monthly_interest, 2),
        }

    months = math.ceil(
        -math.log(1 - (debt_amount * monthly_rate / monthly_payment))
        / math.log(1 + monthly_rate)
    )

    total_paid = months * monthly_payment
    total_interest = total_paid - debt_amount

    return {
        "months": months,
        "years": round(months / 12, 2),
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_interest, 2),
        "warning": None,
    }