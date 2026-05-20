import html
import re
from typing import Any

import streamlit as st

from services.agent_client import ask_agent


st.set_page_config(
    page_title="Personal Finance MCP App",
    layout="wide",
)

MODE_OPTIONS = [
    "Budget Planning",
    "Savings Goal",
    "Debt Payoff",
    "Full Financial Review",
]
FIELD_LABELS = {
    "monthly_income": "Income",
    "rent": "Housing",
    "food": "Food",
    "transport": "Transport",
    "subscriptions": "Subscriptions",
    "entertainment": "Entertainment",
    "savings_goal": "Savings Goal",
    "debt_amount": "Debt",
    "annual_interest_rate": "APR",
    "monthly_debt_payment": "Debt Payment",
    "target_purchase_item": "Target Item",
    "target_purchase_amount": "Target Amount",
}


def _currency(value: float) -> str:
    return f"${value:,.0f}"


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
          background: #0f1117;
          color: #edf1f5;
        }
        section[data-testid="stSidebar"] {
          background: #11131a;
          border-right: 1px solid rgba(255,255,255,0.04);
          min-width: 228px !important;
          max-width: 228px !important;
        }
        section[data-testid="stSidebar"] * {
          color: #eef3f7 !important;
        }
        .block-container {
          max-width: 860px;
          padding-top: 0.85rem;
          padding-bottom: 0.75rem;
        }
        .main-shell {
          max-width: 820px;
          margin: 0 auto;
        }
        .chat-shell {
          background: transparent;
          border: 0;
          padding: 0;
          box-shadow: none;
        }
        .assistant-row, .user-row {
          display: flex;
          align-items: flex-start;
          gap: 0.75rem;
          margin-bottom: 1.05rem;
        }
        .assistant-row {
          justify-content: flex-start;
        }
        .user-row {
          justify-content: flex-start;
        }
        .assistant-icon, .user-icon {
          width: 34px;
          height: 34px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1rem;
          flex: 0 0 34px;
        }
        .assistant-icon {
          background: #ff9800;
          color: #121417;
        }
        .user-icon {
          background: #ff4747;
          color: #fff3f3;
        }
        .assistant-bubble, .user-bubble {
          line-height: 1.52;
          font-size: 0.98rem;
          color: #eef3f7;
          max-width: calc(100% - 48px);
        }
        .user-bubble {
          background: #1b1e27;
          border: 1px solid rgba(255,255,255,0.05);
          border-radius: 10px;
          padding: 0.95rem 1rem;
          width: 100%;
        }
        .section-card {
          background: #191d26;
          border: 1px solid rgba(255,255,255,0.05);
          border-radius: 12px;
          padding: 0.85rem 0.95rem;
          margin-top: 0.55rem;
        }
        div[data-testid="stChatInput"] {
          position: sticky;
          bottom: 0;
          z-index: 20;
          background: linear-gradient(180deg, rgba(15,17,23,0) 0%, rgba(15,17,23,0.92) 26%, rgba(15,17,23,1) 100%);
          padding-top: 0.55rem;
          margin-top: 0.15rem;
        }
        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] input {
          border-radius: 12px !important;
          background: #1a1d26 !important;
          color: #eef3f7 !important;
          border: 1px solid rgba(255,255,255,0.05) !important;
          min-height: 44px !important;
        }
        div[data-testid="stChatInput"] button {
          border-radius: 10px !important;
        }
        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stChatInput"]) {
          position: sticky;
          bottom: 0;
          background: #0f1117;
        }
        [data-testid="stMetric"] {
          background: #1a1d26;
          border: 1px solid rgba(255,255,255,0.05);
          padding: 0.45rem 0.6rem;
          border-radius: 10px;
        }
        [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
          color: #eef3f7 !important;
        }
        .stExpander {
          background: #171a22;
          border: 1px solid rgba(255,255,255,0.05);
          border-radius: 10px;
        }
        .stMarkdown, .stCaption, .stText {
          color: #edf1f5;
        }
        h1 {
          font-size: 1.18rem !important;
          line-height: 1.1 !important;
          margin-bottom: 0.1rem !important;
          color: #f4f7fb !important;
          font-weight: 700 !important;
        }
        .app-subtitle {
          color: rgba(237, 241, 245, 0.58);
          font-size: 0.9rem;
          margin-bottom: 0.8rem;
        }
        .chat-scroll {
          max-height: 70vh;
          overflow-y: auto;
          padding-right: 0.1rem;
        }
        .chat-scroll::-webkit-scrollbar {
          width: 6px;
        }
        .chat-scroll::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.08);
          border-radius: 999px;
        }
        .assistant-bubble ul, .assistant-bubble ol {
          margin-top: 0.5rem;
          margin-bottom: 0.4rem;
        }
        .assistant-bubble li {
          margin-bottom: 0.22rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initial_assistant_message(mode: str) -> dict[str, str]:
    prompts = {
        "Budget Planning": "Tell me about your income and monthly expenses, and I will help you build a practical budget.",
        "Savings Goal": "Tell me what you earn and what you spend each month, and I will help estimate what you can save.",
        "Debt Payoff": "Tell me about your income, essential expenses, and debt situation, and I will help map out payoff options.",
        "Full Financial Review": "Start anywhere. Share what you know about your income, spending, savings, or debt, and I will guide the rest.",
    }
    return {
        "role": "assistant",
        "content": prompts[mode],
        "kind": "elicitation",
    }


def initialize_state() -> None:
    if "mode" not in st.session_state:
        st.session_state["mode"] = "Full Financial Review"
    if "messages" not in st.session_state:
        st.session_state["messages"] = [initial_assistant_message(st.session_state["mode"])]
    if "known_fields" not in st.session_state:
        st.session_state["known_fields"] = {}
    if "missing_fields" not in st.session_state:
        st.session_state["missing_fields"] = []
    if "financial_profile_complete" not in st.session_state:
        st.session_state["financial_profile_complete"] = False
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = None


def reset_conversation(new_mode: str | None = None) -> None:
    mode = new_mode or st.session_state.get("mode", "Full Financial Review")
    st.session_state["mode"] = mode
    st.session_state["messages"] = [initial_assistant_message(mode)]
    st.session_state["known_fields"] = {}
    st.session_state["missing_fields"] = []
    st.session_state["financial_profile_complete"] = False
    st.session_state["session_id"] = None


def prepare_prompt(user_message: str, mode: str) -> str:
    return f"Requested mode: {mode}\nUser message: {user_message}"


def sidebar_controls() -> str:
    with st.sidebar:
        st.markdown("### Personal Finance")
        selected_mode = st.selectbox("Mode", MODE_OPTIONS, index=MODE_OPTIONS.index(st.session_state["mode"]))
        if selected_mode != st.session_state["mode"]:
            reset_conversation(selected_mode)
            st.rerun()
        if st.button("New Conversation", use_container_width=True):
            reset_conversation(selected_mode)
            st.rerun()
    return selected_mode


def render_user_message(content: str) -> None:
    st.markdown(
        f'''
        <div class="user-row">
          <div class="user-icon">😡</div>
          <div class="user-bubble">{html.escape(content)}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def split_analysis_sections(content: str) -> tuple[str, list[tuple[str, str]]]:
    lines = [line.rstrip() for line in content.splitlines()]
    title_pattern = re.compile(r"^(?:#{1,3}\s*|(?:\d+\.)\s*)(.+)$")
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_body: list[str] = []
    intro: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if current_title:
                current_body.append("")
            elif intro:
                intro.append("")
            continue
        match = title_pattern.match(line)
        if match:
            candidate = match.group(1).strip()
            if len(candidate) < 70:
                if current_title:
                    sections.append((current_title, "\n".join(current_body).strip()))
                current_title = candidate
                current_body = []
                continue
        if current_title:
            current_body.append(line)
        else:
            intro.append(line)
    if current_title:
        sections.append((current_title, "\n".join(current_body).strip()))
    return "\n".join(intro).strip(), [(title, body) for title, body in sections if body]


def render_analysis_metrics() -> None:
    known_fields = st.session_state.get("known_fields", {})
    metric_specs = [
        ("Income", known_fields.get("monthly_income")),
        ("Housing", known_fields.get("rent")),
        ("Debt", known_fields.get("debt_amount")),
        ("Target", known_fields.get("target_purchase_amount")),
    ]
    columns = st.columns(len(metric_specs))
    for column, (label, value) in zip(columns, metric_specs):
        with column:
            if value is None:
                st.metric(label, "—")
            else:
                st.metric(label, _currency(float(value)))


def render_assistant_message(message: dict[str, Any]) -> None:
    content = message["content"]
    kind = message.get("kind", "elicitation")
    st.markdown('<div class="assistant-row"><div class="assistant-icon">💼</div><div class="assistant-bubble">', unsafe_allow_html=True)
    if kind != "analysis":
        st.markdown(content)
        st.markdown("</div></div>", unsafe_allow_html=True)
        return

    intro, sections = split_analysis_sections(content)
    if intro:
        st.markdown(intro)
    else:
        st.markdown("Your financial picture is ready. Here is the breakdown.")
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    render_analysis_metrics()
    st.markdown("</div>", unsafe_allow_html=True)

    if sections:
        for title, body in sections:
            with st.expander(title, expanded=False):
                st.markdown(body)
    elif len(content) > 380:
        with st.expander("Detailed analysis", expanded=False):
            st.markdown(content)


def render_chat_history() -> None:
    st.markdown('<div class="chat-shell">', unsafe_allow_html=True)
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    history_container = st.container(border=False)
    with history_container:
        for message in st.session_state["messages"]:
            if message["role"] == "user":
                render_user_message(message["content"])
            else:
                render_assistant_message(message)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def append_user_and_assistant(user_message: str, agent_result: dict[str, Any]) -> None:
    st.session_state["messages"].append(
        {"role": "user", "content": user_message, "kind": "user"}
    )
    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": agent_result["response"],
            "kind": "analysis" if not agent_result.get("needs_more_info", True) else "elicitation",
        }
    )
    st.session_state["session_id"] = agent_result.get("session_id")
    st.session_state["known_fields"] = agent_result.get("known_fields", {})
    st.session_state["missing_fields"] = agent_result.get("missing_fields", [])
    st.session_state["financial_profile_complete"] = not agent_result.get("needs_more_info", True)


def main() -> None:
    inject_styles()
    initialize_state()
    selected_mode = sidebar_controls()

    st.markdown('<div class="main-shell">', unsafe_allow_html=True)
    st.title("Personal Finance Assistant")
    st.markdown(
        '<div class="app-subtitle">Budgeting, savings, debt payoff, and target purchases in one conversation.</div>',
        unsafe_allow_html=True,
    )

    render_chat_history()

    user_message = st.chat_input("Ask anything about your budget, savings, debt, or a target purchase...")
    if not user_message:
        st.markdown("</div>", unsafe_allow_html=True)
        return

    with st.spinner("Thinking..."):
        agent_result = ask_agent(
            prepare_prompt(user_message, selected_mode),
            session_id=st.session_state["session_id"],
            context={
                "known_fields": st.session_state["known_fields"],
                "missing_fields": st.session_state["missing_fields"],
            },
            messages=[
                {"role": message["role"], "content": message["content"]}
                for message in st.session_state["messages"][-12:]
            ],
        )

    append_user_and_assistant(user_message, agent_result)
    st.markdown("</div>", unsafe_allow_html=True)
    st.rerun()


main()
