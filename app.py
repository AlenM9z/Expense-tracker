import streamlit as st
from datetime import date
from google import genai
from supabase import create_client


# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="My Expense Tracker",
    page_icon="💰",
    layout="wide"
)


# =========================================================
# SUPABASE
# =========================================================

try:

    supabase = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

    supabase_available = True

except Exception:

    supabase = None
    supabase_available = False


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
# AUTHENTICATION
# =========================================================

if "user" not in st.session_state:
    st.session_state.user = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
    
def login_user(email, password):

    response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })

    if response.session is None:
        raise Exception("Supabase did not return a login session.")

    st.session_state.user = response.user
    st.session_state.access_token = response.session.access_token
    st.session_state.refresh_token = response.session.refresh_token

    supabase.auth.set_session(
        response.session.access_token,
        response.session.refresh_token
    )
    
def signup_user(email, password):

    response = supabase.auth.sign_up({
        "email": email,
        "password": password
    })

    if response.session is not None:

        supabase.auth.set_session(
            response.session.access_token,
            response.session.refresh_token
        )

    return response
# Restore Supabase session after Streamlit reruns

if (
    st.session_state.access_token
    and st.session_state.refresh_token
):

    try:

        supabase.auth.set_session(
            st.session_state.access_token,
            st.session_state.refresh_token
        )

    except Exception:

        st.session_state.user = None
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        
def logout_user():

    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None

    st.rerun()

# =========================================================
# CHECK SUPABASE
# =========================================================

if not supabase_available:

    st.error(
        "Supabase is not configured correctly."
    )

    st.stop()


# =========================================================
# LOGIN PAGE
# =========================================================

if st.session_state.user is None:

    st.title("💰 My Expense Tracker")

    st.write(
        "Track your expenses privately and use Gemma "
        "to analyze your spending."
    )

    login_tab, signup_tab = st.tabs(
        ["🔐 Login", "📝 Create Account"]
    )


    # -----------------------------------------------------
    # LOGIN
    # -----------------------------------------------------

    with login_tab:

        st.subheader("Login")

        login_email = st.text_input(
            "Email",
            key="login_email"
        )

        login_password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button(
            "Login",
            type="primary",
            key="login_button"
        ):

            if not login_email or not login_password:

                st.warning(
                    "Please enter your email and password."
                )

            else:

                try:

                    login_user(
                        login_email,
                        login_password
                    )

                    st.success(
                        "Login successful!"
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        f"Login failed: {error}"
                    )


    # -----------------------------------------------------
    # SIGN UP
    # -----------------------------------------------------

    with signup_tab:

        st.subheader("Create Account")

        signup_email = st.text_input(
            "Email",
            key="signup_email"
        )

        signup_password = st.text_input(
            "Password",
            type="password",
            key="signup_password"
        )

        signup_password_confirm = st.text_input(
            "Confirm Password",
            type="password",
            key="signup_password_confirm"
        )

        if st.button(
            "Create Account",
            type="primary",
            key="signup_button"
        ):

            if not signup_email or not signup_password:

                st.warning(
                    "Please enter an email and password."
                )

            elif signup_password != signup_password_confirm:

                st.error(
                    "Passwords do not match."
                )

            elif len(signup_password) < 6:

                st.error(
                    "Password must be at least 6 characters."
                )

            else:

                try:

                    response = signup_user(
                        signup_email,
                        signup_password
                    )

                    if response.user is not None:

                        if response.session is not None:

                            st.session_state.user = response.user

                            st.success(
                                "Account created successfully!"
                            )

                            st.rerun()

                        else:

                            st.success(
                                "Account created! "
                                "Please check your email to confirm "
                                "your account, then log in."
                            )

                    else:

                        st.error(
                            "Could not create the account."
                        )

                except Exception as error:

                    st.error(
                        f"Sign-up failed: {error}"
                    )


    st.stop()


# =========================================================
# CURRENT USER
# =========================================================

user = st.session_state.user


# =========================================================
# DATABASE FUNCTIONS
# =========================================================

def get_expenses():

    response = (
        supabase
        .table("expenses")
        .select(
            "id, expense_date, category, description, amount"
        )
        .eq("user_id", user.id)
        .order("expense_date", desc=True)
        .order("id", desc=True)
        .execute()
    )

    expenses = []

    for row in response.data:

        expenses.append(
            (
                row["id"],
                row["expense_date"],
                row["category"],
                row.get("description") or "",
                float(row["amount"])
            )
        )

    return expenses


def get_total():

    expenses = get_expenses()

    return sum(
        expense[4]
        for expense in expenses
    )


def add_expense(
    expense_date,
    category,
    description,
    amount
):

    supabase.table("expenses").insert({
        "user_id": user.id,
        "expense_date": str(expense_date),
        "category": category,
        "description": description,
        "amount": amount
    }).execute()


def delete_expense(expense_id):

    (
        supabase
        .table("expenses")
        .delete()
        .eq("id", expense_id)
        .eq("user_id", user.id)
        .execute()
    )


# =========================================================
# GEMMA
# =========================================================

def ask_gemma(question):

    expenses = get_expenses()

    if not expenses:

        return "There are no expenses to analyze yet."

    expense_text = ""

    for expense in expenses:

        (
            expense_id,
            expense_date,
            category,
            description,
            amount
        ) = expense

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
# USER INFORMATION
# =========================================================

user_col1, user_col2 = st.columns(
    [4, 1]
)

with user_col1:

    st.caption(
        f"Logged in as: {user.email}"
    )

with user_col2:

    if st.button(
        "Logout"
    ):

        logout_user()


# =========================================================
# SUMMARY
# =========================================================

expenses = get_expenses()

total = sum(
    expense[4]
    for expense in expenses
)

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

        try:

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

        except Exception as error:

            st.error(
                f"Could not add expense: {error}"
            )


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

        (
            expense_id,
            expense_date,
            category,
            description,
            amount
        ) = expense

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

                try:

                    delete_expense(
                        expense_id
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        f"Could not delete expense: {error}"
                    )


st.divider()


# =========================================================
# CATEGORY SUMMARY
# =========================================================

st.header("📊 Spending by Category")

category_totals = {}

for expense in expenses:

    category = expense[2]
    amount = expense[4]

    category_totals[category] = (
        category_totals.get(category, 0)
        + amount
    )


category_data = sorted(
    category_totals.items(),
    key=lambda item: item[1],
    reverse=True
)


if category_data:

    for category, amount in category_data:

        st.write(
            f"**{category}** — ₹{amount:,.2f}"
        )

        percentage = 0

        if total > 0:

            percentage = int(
                (amount / total) * 100
            )

        st.progress(
            min(percentage, 100)
        )

else:

    st.info(
        "Category information will appear here "
        "after you add expenses."
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
    "Expense Tracker • Powered by Python, Streamlit, Supabase and Gemma"
)
