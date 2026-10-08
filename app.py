import streamlit as st
import sqlite3
from datetime import date
from google import genai


# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="My Expense Tracker",
    page_icon="💰",
    layout="wide"
)


# =========================================================
# DATABASE
# =========================================================

DB_FILE = "expenses.db"

conn = sqlite3.connect(
    DB_FILE,
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    amount REAL NOT NULL
)
""")

conn.commit()


# =========================================================
# GEMMA
# =========================================================

try:

    gemma = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )

    gemma_available = True

except Exception:

    gemma = None
    gemma_available = False


# =========================================================
# FUNCTIONS
# =========================================================

def get_expenses():

    cursor.execute("""
        SELECT id, date, category, description, amount
        FROM expenses
        ORDER BY date DESC, id DESC
    """)

    return cursor.fetchall()


def get_total():

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
    """)

    return cursor.fetchone()[0]


def add_expense(
    expense_date,
    category,
    description,
    amount
):

    cursor.execute(
        """
        INSERT INTO expenses
        (date, category, description, amount)
        VALUES (?, ?, ?, ?)
        """,
        (
            str(expense_date),
            category,
            description,
            amount
        )
    )

    conn.commit()


def delete_expense(expense_id):

    cursor.execute(
        "DELETE FROM expenses WHERE id = ?",
        (expense_id,)
    )

    conn.commit()


def ask_gemma(question):

    expenses = get_expenses()

    if not expenses:
        return "There are no expenses to analyze yet."

    expense_text = ""

    for expense in expenses:

        expense_id, expense_date, category, description, amount = expense

        expense_text += (
            f"Date: {expense_date} | "
            f"Category: {category} | "
            f"Description: {description} | "
            f"Amount: ₹{amount:.2f}\n"
        )

    prompt = f"""
You are an expense tracking assistant.

Here is the user's expense data:

{expense_text}

The user asks:

{question}

Answer using ONLY the provided expense data.

Rules:

1. Use Indian Rupees (₹).
2. Calculate totals carefully.
3. Never invent an expense.
4. If the data doesn't contain the answer, say so.
5. Keep the answer easy to understand.
"""

    response = gemma.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=prompt
    )

    return response.text


# =========================================================
# HEADER
# =========================================================

st.title("💰 My Expense Tracker")

st.write(
    "Track your expenses and use Gemma to analyze your spending."
)


# =========================================================
# SUMMARY
# =========================================================

expenses = get_expenses()

total = get_total()

number_of_expenses = len(expenses)

largest_expense = 0

if expenses:

    largest_expense = max(
        expense[4]
        for expense in expenses
    )


col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Total Spending",
        f"₹{total:,.2f}"
    )

with col2:

    st.metric(
        "Number of Expenses",
        number_of_expenses
    )

with col3:

    st.metric(
        "Largest Expense",
        f"₹{largest_expense:,.2f}"
    )


st.divider()


# =========================================================
# ADD EXPENSE
# =========================================================

st.header("➕ Add Expense")

col1, col2 = st.columns(2)

with col1:

    expense_date = st.date_input(
        "Date",
        value=date.today()
    )

    category = st.selectbox(
        "Category",
        [
            "Food",
            "Transport",
            "Shopping",
            "Bills",
            "Entertainment",
            "Education",
            "Health",
            "Rent",
            "Other"
        ]
    )


with col2:

    description = st.text_input(
        "Description",
        placeholder="Example: Lunch at restaurant"
    )

    amount = st.number_input(
        "Amount (₹)",
        min_value=0.0,
        step=10.0
    )


if st.button(
    "Add Expense",
    type="primary"
):

    if amount <= 0:

        st.error(
            "Please enter an amount greater than ₹0."
        )

    else:

        add_expense(
            expense_date,
            category,
            description,
            amount
        )

        st.success(
            "Expense added successfully!"
        )

        st.rerun()


st.divider()


# =========================================================
# EXPENSE LIST
# =========================================================

st.header("📋 Your Expenses")

expenses = get_expenses()

if not expenses:

    st.info(
        "You haven't added any expenses yet."
    )

else:

    for expense in expenses:

        expense_id = expense[0]
        expense_date = expense[1]
        category = expense[2]
        description = expense[3]
        amount = expense[4]

        col1, col2, col3, col4, col5 = st.columns(
            [1.2, 1.5, 2, 1.2, 1]
        )

        with col1:

            st.write(
                expense_date
            )

        with col2:

            st.write(
                category
            )

        with col3:

            st.write(
                description
            )

        with col4:

            st.write(
                f"₹{amount:,.2f}"
            )

        with col5:

            if st.button(
                "Delete",
                key=f"delete_{expense_id}"
            ):

                delete_expense(
                    expense_id
                )

                st.rerun()


st.divider()


# =========================================================
# CATEGORY SUMMARY
# =========================================================

st.header("📊 Spending by Category")

cursor.execute("""
    SELECT category, SUM(amount)
    FROM expenses
    GROUP BY category
    ORDER BY SUM(amount) DESC
""")

category_data = cursor.fetchall()

if category_data:

    for category, amount in category_data:

        st.write(
            f"**{category}** — ₹{amount:,.2f}"
        )

        st.progress(
            min(
                int(
                    (amount / total) * 100
                ),
                100
            )
        )

else:

    st.info(
        "Category information will appear here after you add expenses."
    )


st.divider()


# =========================================================
# GEMMA
# =========================================================

st.header("🤖 Ask Gemma")

if not gemma_available:

    st.warning(
        "Gemma is not configured yet."
    )

    st.write(
        "Your local Gemma API test works, but Streamlit needs "
        "the API key in its secrets file."
    )

else:

    st.success(
        "Gemma is connected."
    )

    question = st.text_input(
        "Ask something about your expenses",
        placeholder="How much did I spend on food?"
    )

    if st.button(
        "🤖 Ask Gemma",
        type="primary"
    ):

        if not question:

            st.warning(
                "Please enter a question."
            )

        else:

            with st.spinner(
                "Gemma is analyzing your expenses..."
            ):

                try:

                    answer = ask_gemma(
                        question
                    )

                    st.subheader(
                        "Gemma's Answer"
                    )

                    st.write(
                        answer
                    )

                except Exception as error:

                    st.error(
                        f"Gemma API error: {error}"
                    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Expense Tracker • Powered by Python, Streamlit and Gemma"
)
