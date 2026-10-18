"""RAMANUJAN 2.O — refined Streamlit chatbot prototype.

Run locally:
    pip install -r requirements_ramanujan.txt
    streamlit run ramanujan_2o_refined.py

For genuine model-powered answers, set OPENAI_API_KEY in your environment and
install the optional `openai` package. Without a key, the app uses a small
rule-based fallback and clearly indicates that mode.
"""

from __future__ import annotations

import html
import os
import random
import time
from datetime import datetime
from typing import Optional

import streamlit as st

st.set_page_config(
    page_title="RAMANUJAN 2.O",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp { background: #050B14; color: #E2E8F0; }
    [data-testid="stHeader"] { background: rgba(5,11,20,0); }
    .company-title { color:#38BDF8; font-weight:800; font-size:.8rem;
        letter-spacing:.18em; margin-bottom:0; }
    .app-title { color:#fff; font-size:2.25rem; font-weight:750;
        margin-top:0; margin-bottom:.3rem; }
    .subtle { color:#94A3B8; }
    div[data-testid="stChatMessage"] { background:#0A192F;
        border:1px solid #172A45; border-radius:12px; }
    .stTextInput input, .stTextArea textarea { background:#0B1528!important;
        color:#fff!important; border:1px solid #1E293B!important; }
    .stButton button, .stFormSubmitButton button { border-radius:9px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Session state ----------
DEFAULTS = {
    "step": "name_entry",
    "user_name": "",
    "chat_history": [],
    "question_count": 0,
    "learned_memory": {},
    "evaluating": False,
    "pending_question": "",
    "option_a": "",
    "option_b": "",
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value

# ---------- Response engine ----------
def fallback_response(query: str, memory: dict[str, str]) -> str:
    """Transparent offline fallback; this is not a trained language model."""
    q = query.strip().lower()
    memory_note = ""
    # Prefer the most recent relevant saved note, using whole-word-ish substring matching.
    for key, value in reversed(list(memory.items())):
        if key and key in q:
            memory_note = f"\n\nFrom our saved chat note about **{key}**: {value}"
            break

    if any(word in q for word in ("hello", "hi", "hey", "namaste")):
        answer = f"Hello {st.session_state.user_name}! What would you like to work on today?"
    elif any(word in q for word in ("news", "latest", "today")):
        answer = (
            f"Today is {datetime.now().strftime('%B %d, %Y')}. I do not have live news access "
            "in offline mode, so I cannot verify current headlines. Connect a live information "
            "source or enable the language-model mode for broader assistance."
        )
    elif any(word in q for word in ("profit", "business", "company")):
        answer = (
            "A useful starting point is to define the customer, quantify the problem, estimate "
            "unit economics, and test demand before scaling. If you share the industry, costs, "
            "price, and expected sales, I can help structure a more specific analysis."
        )
    elif any(word in q for word in ("who are you", "your name", "ramanujan")):
        answer = (
            "I am RAMANUJAN 2.O, a chatbot prototype. In offline mode I use a small set of "
            "rules and saved conversation notes; I am not independently reasoning with a trained model."
        )
    else:
        answer = (
            "I can help you think this through, but my offline response engine is limited. "
            "Please add context, your goal, and any constraints so I can give a more useful response."
        )
    return answer + memory_note


def model_response(query: str, variant: str = "primary") -> str:
    """Use OpenAI if configured; otherwise use the offline fallback."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            history = [
                {"role": item["role"], "content": item["text"]}
                for item in st.session_state.chat_history[-10:]
                if item["role"] in ("user", "assistant")
            ]
            system_prompt = (
                "You are RAMANUJAN 2.O, a respectful, clear, honest assistant. "
                "Do not claim to have performed actions or checked live information unless true. "
                "Explain uncertainty and give practical answers."
            )
            if variant == "secondary":
                system_prompt += " Offer a distinct alternative approach to the user's question."
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "system", "content": system_prompt}, *history,
                          {"role": "user", "content": query}],
                temperature=0.7 if variant == "primary" else 0.9,
            )
            content = response.choices[0].message.content
            if content:
                return content.strip()
            return "I could not produce a response this time. Please try again."
        except Exception as exc:
            # Keep technical detail out of the user-facing chat, but show it in app status.
            st.session_state.last_model_error = str(exc)
            return fallback_response(query, st.session_state.learned_memory)
    return fallback_response(query, st.session_state.learned_memory)


def save_exchange(question: str, answer: str) -> None:
    st.session_state.chat_history.append({"role": "user", "text": question})
    st.session_state.chat_history.append({"role": "assistant", "text": answer})
    # Store the actual question and answer, rather than arbitrary final words.
    st.session_state.learned_memory[question.strip().lower()] = answer[:240]
    # Avoid unbounded session growth.
    st.session_state.chat_history = st.session_state.chat_history[-100:]
    st.session_state.learned_memory = dict(list(st.session_state.learned_memory.items())[-50:])

# ---------- Header ----------
st.markdown('<p class="company-title">VIDRENCE</p>', unsafe_allow_html=True)
st.markdown('<h1 class="app-title">RAMANUJAN 2.O</h1>', unsafe_allow_html=True)
api_enabled = bool(os.getenv("OPENAI_API_KEY", "").strip())
if api_enabled:
    st.caption("Model-powered mode enabled · Responses may still need verification")
else:
    st.caption("Offline prototype mode · Set OPENAI_API_KEY to enable model-powered responses")

# ---------- Name entry ----------
if st.session_state.step == "name_entry":
    st.write("### Welcome to the Inner Circle Engine")
    with st.form("identity_form"):
        name_input = st.text_input("What should I call you?", max_chars=60)
        start = st.form_submit_button("Initialize Chatbot", use_container_width=True)
    if start:
        clean_name = name_input.strip()
        if clean_name:
            st.session_state.user_name = clean_name
            st.session_state.step = "active_chat"
            st.rerun()
        else:
            st.error("Please enter a name before continuing.")
else:
    left, right = st.columns([1, 10])
    with left:
        st.markdown("<div style='font-size:2rem'>◉</div>", unsafe_allow_html=True)
    with right:
        st.markdown(f"<p class='subtle'>Ask your questions, {html.escape(st.session_state.user_name)}.</p>", unsafe_allow_html=True)

    for item in st.session_state.chat_history:
        role = "user" if item["role"] == "user" else "assistant"
        with st.chat_message(role, avatar="👤" if role == "user" else "🧠"):
            st.markdown(item["text"])

    if st.session_state.evaluating:
        st.warning("Feedback checkpoint: choose the response you prefer to continue.")
        st.markdown("**Your question**")
        st.write(st.session_state.pending_question)
        with st.expander("Response Model Alpha", expanded=True):
            st.markdown(st.session_state.option_a)
        with st.expander("Response Model Beta", expanded=True):
            st.markdown(st.session_state.option_b)
        with st.form("feedback_form"):
            choice = st.radio(
                "Which response is more useful?",
                ["Select a response", "Response Model Alpha", "Response Model Beta"],
                index=0,
            )
            submit_feedback = st.form_submit_button("Submit Feedback", use_container_width=True)
        if submit_feedback:
            if choice == "Select a response":
                st.error("Choose Alpha or Beta to continue.")
            else:
                answer = st.session_state.option_a if choice.endswith("Alpha") else st.session_state.option_b
                save_exchange(st.session_state.pending_question, answer)
                st.session_state.evaluating = False
                st.session_state.pending_question = ""
                st.session_state.option_a = ""
                st.session_state.option_b = ""
                st.rerun()
    else:
        with st.form("chat_input_form", clear_on_submit=True):
            user_input = st.text_input("Message", placeholder="Ask RAMANUJAN 2.O…", max_chars=4000)
            submitted = st.form_submit_button("Send", use_container_width=True)
        if submitted:
            question = user_input.strip()
            if question:
                st.session_state.question_count += 1
                if st.session_state.question_count % 10 == 0:
                    with st.spinner("Generating two responses…"):
                        st.session_state.option_a = model_response(question, "primary")
                        st.session_state.option_b = model_response(question, "secondary")
                    st.session_state.pending_question = question
                    st.session_state.evaluating = True
                    st.rerun()
                else:
                    with st.spinner("Thinking…"):
                        answer = model_response(question, "primary")
                    save_exchange(question, answer)
                    st.rerun()

    with st.sidebar:
        st.subheader("Session controls")
        st.caption(f"Questions asked: {st.session_state.question_count}")
        if st.button("Clear chat and restart", use_container_width=True):
            for key, value in DEFAULTS.items():
                st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value
            st.rerun()
        if st.button("Show saved notes", use_container_width=True):
            st.json(st.session_state.learned_memory)
        if "last_model_error" in st.session_state:
            st.warning("The model request failed; offline fallback was used.")
            st.caption(st.session_state.last_model_error[:500])
