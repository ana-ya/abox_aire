import json
from typing import Any

import streamlit as st

from services.agent_client import ask_agent


st.set_page_config(
    page_title="Personal Finance MCP App",
    layout="wide",
)


def _currency(value: float) -> str:
    return f"${value:,.2f}"


def build_agent_prompt(data: dict[str, Any], focus_area: str) -> str:
    payload = {
        "monthly_income": data["monthly_income"],
        "rent": data["rent"],
        "food": data["food"],
        "transport": data["transport"],
        "subscriptions": data["subscriptions"],
        "entertainment": data["entertainment"],
        "savings_goal": data["savings_goal"],
        "debt_amount": data["debt_amount"],
        "annual_interest_rate": data["annual_interest_rate"],
        "monthly_debt_payment": data["monthly_debt_payment"],
    }
    return f"""
You are supporting the Personal Finance MCP App.

Use the available MCP tools through the ADK agent workflow to analyze the user's financial situation.
Do not ask the UI for more calculations. Perform the analysis with tools and reasoning on the agent side.

Primary focus area: {focus_area}

User financial inputs:
{json.dumps(payload, indent=2)}

Please return a concise but useful response with these sections:
1. Monthly Budget Planner
2. Expense Analyzer
3. Debt Payoff Estimator
4. AI Financial Recommendation

For each section, explain the result in plain language. If any assumption is needed, state it clearly.
""".strip()


st.title("Personal Finance MCP App")
st.caption("Streamlit UI for an ADK agent that uses MCP tools for financial guidance.")

with st.sidebar:
    st.header("Agent Settings")
    st.write(
        "This UI sends a natural-language request to the ADK agent defined by "
        "`ADK_AGENT_URL` and displays the response."
    )
    focus_area = st.selectbox(
        "Demo focus",
        (
            "Full financial review",
            "Monthly Budget Planner",
            "Expense Analyzer",
            "Debt Payoff Estimator",
            "AI Financial Recommendation",
        ),
    )

section_tabs = st.tabs(
    [
        "Monthly Budget Planner",
        "Expense Analyzer",
        "Debt Payoff Estimator",
        "AI Financial Recommendation",
    ]
)

section_descriptions = [
    "Collect income, spending, and savings inputs for a monthly budget review.",
    "Send recurring expense details for spending-pattern analysis.",
    "Capture debt balance, interest rate, and payment details for payoff guidance.",
    "Ask the agent to synthesize the full picture into next-step recommendations.",
]

for tab, description in zip(section_tabs, section_descriptions):
    with tab:
        st.write(description)

with st.form("personal_finance_form"):
    st.subheader("Financial Inputs")
    col1, col2 = st.columns(2)

    with col1:
        monthly_income = st.number_input(
            "Monthly income",
            min_value=0.0,
            value=5000.0,
            step=100.0,
            format="%.2f",
        )
        rent = st.number_input(
            "Rent",
            min_value=0.0,
            value=1500.0,
            step=50.0,
            format="%.2f",
        )
        food = st.number_input(
            "Food",
            min_value=0.0,
            value=500.0,
            step=25.0,
            format="%.2f",
        )
        transport = st.number_input(
            "Transport",
            min_value=0.0,
            value=250.0,
            step=25.0,
            format="%.2f",
        )
        subscriptions = st.number_input(
            "Subscriptions",
            min_value=0.0,
            value=75.0,
            step=5.0,
            format="%.2f",
        )

    with col2:
        entertainment = st.number_input(
            "Entertainment",
            min_value=0.0,
            value=200.0,
            step=25.0,
            format="%.2f",
        )
        savings_goal = st.number_input(
            "Savings goal",
            min_value=0.0,
            value=600.0,
            step=25.0,
            format="%.2f",
        )
        debt_amount = st.number_input(
            "Debt amount",
            min_value=0.0,
            value=12000.0,
            step=100.0,
            format="%.2f",
        )
        annual_interest_rate = st.number_input(
            "Annual interest rate (%)",
            min_value=0.0,
            value=18.5,
            step=0.1,
            format="%.2f",
        )
        monthly_debt_payment = st.number_input(
            "Monthly debt payment",
            min_value=0.0,
            value=400.0,
            step=25.0,
            format="%.2f",
        )

    submitted = st.form_submit_button("Ask the ADK Agent", type="primary")

if submitted:
    form_data = {
        "monthly_income": monthly_income,
        "rent": rent,
        "food": food,
        "transport": transport,
        "subscriptions": subscriptions,
        "entertainment": entertainment,
        "savings_goal": savings_goal,
        "debt_amount": debt_amount,
        "annual_interest_rate": annual_interest_rate,
        "monthly_debt_payment": monthly_debt_payment,
    }

    with st.expander("Submitted Inputs", expanded=False):
        st.write(
            {
                "monthly_income": _currency(monthly_income),
                "rent": _currency(rent),
                "food": _currency(food),
                "transport": _currency(transport),
                "subscriptions": _currency(subscriptions),
                "entertainment": _currency(entertainment),
                "savings_goal": _currency(savings_goal),
                "debt_amount": _currency(debt_amount),
                "annual_interest_rate": f"{annual_interest_rate:.2f}%",
                "monthly_debt_payment": _currency(monthly_debt_payment),
            }
        )

    prompt = build_agent_prompt(form_data, focus_area)

    with st.spinner("Contacting the ADK agent..."):
        agent_response = ask_agent(prompt)

    st.subheader("Agent Response")
    st.markdown(agent_response)
