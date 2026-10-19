from datetime import date
from decimal import Decimal

import mysql.connector
import pandas as pd
import streamlit as st

from db import get_connection


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Smart Expense Tracker",
    page_icon="💰",
    layout="wide",
)

st.title("💰 Smart Expense Tracker")
st.caption("Manage your income, expenses and monthly budgets.")


# --------------------------------------------------
# DATABASE HELPER
# --------------------------------------------------

def run_query(query, params=None, fetch=False, dictionary=False):
    """Execute a database query and close the connection safely."""
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=dictionary)
        cursor.execute(query, params or ())

        if fetch:
            return cursor.fetchall()

        connection.commit()
        return True

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


# --------------------------------------------------
# ADD EXPENSE
# --------------------------------------------------

st.header("➖ Add an Expense")

with st.form("add_expense_form"):
    expense_col1, expense_col2 = st.columns(2)

    with expense_col1:
        expense_amount = st.number_input(
            "Amount (₹)",
            min_value=0.01,
            value=100.0,
            step=1.0,
            key="new_expense_amount",
        )

        expense_category = st.selectbox(
            "Category",
            ["Food", "Travel", "Shopping", "Bills", "Health", "Other"],
        )

    with expense_col2:
        expense_description = st.text_input(
            "Description (optional)",
            placeholder="e.g. Lunch",
        )

        expense_date = st.date_input(
            "Expense date",
            value=date.today(),
        )

    save_expense = st.form_submit_button(
        "Save expense",
        use_container_width=True,
    )

if save_expense:
    try:
        run_query(
            """
            INSERT INTO expenses
                (amount, category, description, expense_date)
            VALUES (%s, %s, %s, %s)
            """,
            (
                Decimal(str(expense_amount)),
                expense_category,
                expense_description.strip() or None,
                expense_date,
            ),
        )

        st.success("Expense saved successfully! ✅")

    except mysql.connector.Error as error:
        st.error(f"Could not save expense: {error}")


st.divider()


# --------------------------------------------------
# ADD INCOME
# --------------------------------------------------

st.header("➕ Add Income")

with st.form("add_income_form"):
    income_col1, income_col2 = st.columns(2)

    with income_col1:
        income_amount = st.number_input(
            "Income amount (₹)",
            min_value=0.01,
            value=5000.0,
            step=100.0,
            key="new_income_amount",
        )

        income_source = st.text_input(
            "Income source",
            placeholder="e.g. Part-time Work",
        )

    with income_col2:
        income_date = st.date_input(
            "Income date",
            value=date.today(),
        )

    save_income = st.form_submit_button(
        "Save income",
        use_container_width=True,
    )

if save_income:
    st.write("DEBUG: Save Income button clicked")
    if not income_source.strip():
        st.warning("Please enter an income source.")

    else:
        try:
            run_query(
                """
                INSERT INTO income (amount, source, income_date)
                VALUES (%s, %s, %s)
                """,
                (
                    Decimal(str(income_amount)),
                    income_source.strip(),
                    income_date,
                ),
            )

            st.success("Income saved successfully! ✅")

        except mysql.connector.Error as error:
            st.error(f"Could not save income: {error}")


st.divider()


# --------------------------------------------------
# LOAD EXPENSES AND INCOME
# --------------------------------------------------

try:
    expense_rows = run_query(
        """
        SELECT id, expense_date, category, description, amount
        FROM expenses
        ORDER BY expense_date DESC, id DESC
        """,
        fetch=True,
        dictionary=True,
    )

    income_rows = run_query(
        """
        SELECT id, income_date, source, amount
        FROM income
        ORDER BY income_date DESC, id DESC
        """,
        fetch=True,
        dictionary=True,
    )

    expenses_df = pd.DataFrame(expense_rows)
    income_df = pd.DataFrame(income_rows)

except mysql.connector.Error as error:
    st.error(f"Could not load data from the database: {error}")
    st.stop()


# --------------------------------------------------
# DASHBOARD SUMMARY
# --------------------------------------------------

st.header("📊 Dashboard")

today = date.today()
month_start = today.replace(day=1)

if today.month == 12:
    next_month_start = date(today.year + 1, 1, 1)
else:
    next_month_start = date(today.year, today.month + 1, 1)


if not expenses_df.empty:
    expenses_df["amount"] = expenses_df["amount"].astype(float)
    expenses_df["expense_date"] = pd.to_datetime(
        expenses_df["expense_date"]
    ).dt.date

    monthly_expenses_df = expenses_df[
        (expenses_df["expense_date"] >= month_start)
        & (expenses_df["expense_date"] < next_month_start)
    ]

    total_expenses = float(expenses_df["amount"].sum())
    monthly_spending = float(monthly_expenses_df["amount"].sum())

else:
    monthly_expenses_df = pd.DataFrame()
    total_expenses = 0.0
    monthly_spending = 0.0


if not income_df.empty:
    income_df["amount"] = income_df["amount"].astype(float)
    income_df["income_date"] = pd.to_datetime(
        income_df["income_date"]
    ).dt.date

    monthly_income_df = income_df[
        (income_df["income_date"] >= month_start)
        & (income_df["income_date"] < next_month_start)
    ]

    total_income = float(income_df["amount"].sum())
    monthly_income = float(monthly_income_df["amount"].sum())

else:
    monthly_income_df = pd.DataFrame()
    total_income = 0.0
    monthly_income = 0.0


monthly_balance = monthly_income - monthly_spending

metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric("Total Income", f"₹{total_income:,.2f}")
metric2.metric("Total Expenses", f"₹{total_expenses:,.2f}")
metric3.metric("Monthly Income", f"₹{monthly_income:,.2f}")
metric4.metric(
    "Monthly Balance",
    f"₹{monthly_balance:,.2f}",
)

if monthly_balance < 0:
    st.warning(
        f"Your expenses exceed your income by "
        f"₹{abs(monthly_balance):,.2f} this month."
    )


st.divider()


# --------------------------------------------------
# INCOME HISTORY
# --------------------------------------------------

st.header("💵 Income History")

if income_df.empty:
    st.info("No income recorded yet.")

else:
    income_display = income_df[
        ["income_date", "source", "amount"]
    ].copy()

    income_display = income_display.sort_values(
        "income_date",
        ascending=False,
    )

    st.dataframe(
        income_display,
        hide_index=True,
        use_container_width=True,
    )


st.divider()


# --------------------------------------------------
# EXPENSE HISTORY
# --------------------------------------------------

st.header("🧾 Your Expenses")

if expenses_df.empty:
    st.info("No expenses yet. Add your first expense above.")

else:
    st.dataframe(
        expenses_df[
            ["id", "expense_date", "category", "description", "amount"]
        ],
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Edit an Expense")

    expense_options = {
        int(row["id"]): row
        for row in expense_rows
    }

    selected_id = st.selectbox(
        "Choose an expense to edit",
        options=list(expense_options.keys()),
        format_func=lambda expense_id: (
            f"#{expense_id} — "
            f"{expense_options[expense_id]['category']} — "
            f"₹{float(expense_options[expense_id]['amount']):,.2f}"
        ),
    )

    selected_expense = expense_options[selected_id]

    categories = [
        "Food",
        "Travel",
        "Shopping",
        "Bills",
        "Health",
        "Other",
    ]

    with st.form("edit_expense_form"):
        edit_amount = st.number_input(
            "Updated amount (₹)",
            min_value=0.01,
            value=float(selected_expense["amount"]),
            step=1.0,
        )

        original_category = selected_expense["category"]

        edit_category = st.selectbox(
            "Updated category",
            categories,
            index=(
                categories.index(original_category)
                if original_category in categories
                else 0
            ),
        )

        edit_description = st.text_input(
            "Updated description",
            value=selected_expense["description"] or "",
        )

        edit_date = st.date_input(
            "Updated expense date",
            value=pd.to_datetime(
                selected_expense["expense_date"]
            ).date(),
        )

        update_expense = st.form_submit_button("Update expense")

    if update_expense:
        try:
            run_query(
                """
                UPDATE expenses
                SET amount = %s,
                    category = %s,
                    description = %s,
                    expense_date = %s
                WHERE id = %s
                """,
                (
                    Decimal(str(edit_amount)),
                    edit_category,
                    edit_description.strip() or None,
                    edit_date,
                    selected_id,
                ),
            )

            st.success("Expense updated successfully! ✅")
            st.rerun()

        except mysql.connector.Error as error:
            st.error(f"Could not update expense: {error}")

    st.subheader("Delete an Expense")

    confirm_delete = st.checkbox(
        "I understand this expense will be permanently deleted."
    )

    if st.button("Delete selected expense"):
        if not confirm_delete:
            st.warning("Confirm deletion using the checkbox first.")

        else:
            try:
                run_query(
                    "DELETE FROM expenses WHERE id = %s",
                    (selected_id,),
                )

                st.success("Expense deleted successfully! ✅")
                st.rerun()

            except mysql.connector.Error as error:
                st.error(f"Could not delete expense: {error}")


st.divider()


# --------------------------------------------------
# FILTER AND EXPORT EXPENSES
# --------------------------------------------------

st.header("🔎 Find and Export Expenses")

if expenses_df.empty:
    st.info("Add an expense to use filters and CSV export.")

else:
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        chosen_category = st.selectbox(
            "Filter by category",
            ["All"] + sorted(expenses_df["category"].dropna().unique()),
        )

    with filter_col2:
        search_text = st.text_input(
            "Search description",
            placeholder="e.g. groceries",
        )

    min_date = min(expenses_df["expense_date"])
    max_date = max(expenses_df["expense_date"])

    date_col1, date_col2 = st.columns(2)

    with date_col1:
        start_date = st.date_input(
            "From date",
            value=min_date,
            key="filter_start_date",
        )

    with date_col2:
        end_date = st.date_input(
            "To date",
            value=max_date,
            key="filter_end_date",
        )

    if start_date > end_date:
        st.warning("From date must be on or before To date.")

    else:
        filtered_df = expenses_df[
            expenses_df["expense_date"].between(start_date, end_date)
        ].copy()

        if chosen_category != "All":
            filtered_df = filtered_df[
                filtered_df["category"] == chosen_category
            ]

        if search_text.strip():
            filtered_df = filtered_df[
                filtered_df["description"]
                .fillna("")
                .str.contains(
                    search_text.strip(),
                    case=False,
                    regex=False,
                )
            ]

        st.write(f"**{len(filtered_df)} expense(s) found**")

        st.metric(
            "Filtered expense total",
            f"₹{filtered_df['amount'].sum():,.2f}",
        )

        st.dataframe(
            filtered_df,
            hide_index=True,
            use_container_width=True,
        )

        export_df = filtered_df.copy()
        export_df["expense_date"] = export_df[
            "expense_date"
        ].astype(str)

        st.download_button(
            "Download expenses as CSV",
            data=export_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="expenses.csv",
            mime="text/csv",
        )


st.divider()


# --------------------------------------------------
# SPENDING BY CATEGORY
# --------------------------------------------------

st.header("📈 Spending by Category")

if expenses_df.empty:
    st.info("Add expenses to see your category chart.")

else:
    category_totals = (
        expenses_df.groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
    )

    st.bar_chart(
        category_totals,
        x="category",
        y="amount",
    )


st.divider()


# --------------------------------------------------
# MONTHLY BUDGET
# --------------------------------------------------

current_month = today.strftime("%Y-%m")

st.header(f"🎯 Monthly Budget — {current_month}")

try:
    budget_rows = run_query(
        """
        SELECT budget_amount
        FROM monthly_budgets
        WHERE budget_month = %s
        """,
        (current_month,),
        fetch=True,
    )

    saved_budget = (
        float(budget_rows[0][0])
        if budget_rows
        else 1000.0
    )

    with st.form("monthly_budget_form"):
        budget_input = st.number_input(
            "Monthly budget (₹)",
            min_value=1.0,
            value=saved_budget,
            step=100.0,
        )

        save_budget = st.form_submit_button("Save monthly budget")

    if save_budget:
        run_query(
            """
            INSERT INTO monthly_budgets
                (budget_month, budget_amount)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE budget_amount = %s
            """,
            (
                current_month,
                Decimal(str(budget_input)),
                Decimal(str(budget_input)),
            ),
        )

        st.success("Monthly budget saved! ✅")
        saved_budget = budget_input

    budget_remaining = saved_budget - monthly_spending

    st.metric(
        "Budget remaining",
        f"₹{budget_remaining:,.2f}",
    )

    if budget_remaining < 0:
        st.warning(
            f"Budget exceeded by ₹{abs(budget_remaining):,.2f}."
        )

except mysql.connector.Error as error:
    st.error(f"Could not load or save monthly budget: {error}")


st.divider()


# --------------------------------------------------
# CATEGORY BUDGETS
# --------------------------------------------------

st.header("📂 Category Budgets")

budget_categories = [
    "Food",
    "Travel",
    "Shopping",
    "Bills",
    "Health",
    "Other",
]

with st.form("category_budget_form"):
    budget_category = st.selectbox(
        "Select category",
        budget_categories,
    )

    category_limit = st.number_input(
        "Monthly category limit (₹)",
        min_value=1.0,
        value=1000.0,
        step=100.0,
    )

    save_category_budget = st.form_submit_button(
        "Save category budget"
    )

if save_category_budget:
    try:
        run_query(
            """
            INSERT INTO category_budgets
                (budget_month, category, budget_amount)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE budget_amount = %s
            """,
            (
                current_month,
                budget_category,
                Decimal(str(category_limit)),
                Decimal(str(category_limit)),
            ),
        )

        st.success(
            f"{budget_category} budget saved successfully! ✅"
        )
        st.rerun()

    except mysql.connector.Error as error:
        st.error(f"Could not save category budget: {error}")


try:
    category_budget_rows = run_query(
        """
        SELECT category, budget_amount
        FROM category_budgets
        WHERE budget_month = %s
        """,
        (current_month,),
        fetch=True,
    )

    if category_budget_rows:
        budget_df = pd.DataFrame(
            category_budget_rows,
            columns=["Category", "Budget (₹)"],
        )

        if expenses_df.empty:
            spent_by_category = {}

        else:
            current_expenses = expenses_df[
                expenses_df["expense_date"].apply(
                    lambda value: value.strftime("%Y-%m") == current_month
                )
            ]

            spent_by_category = (
                current_expenses.groupby("category")["amount"]
                .sum()
                .to_dict()
            )

        budget_df["Spent (₹)"] = budget_df["Category"].map(
            spent_by_category
        ).fillna(0.0)

        budget_df["Remaining (₹)"] = (
            budget_df["Budget (₹)"] - budget_df["Spent (₹)"]
        )

        st.dataframe(
            budget_df,
            hide_index=True,
            use_container_width=True,
        )

        for _, row in budget_df.iterrows():
            if row["Remaining (₹)"] < 0:
                st.warning(
                    f"{row['Category']} budget exceeded by "
                    f"₹{abs(row['Remaining (₹)']):,.2f}."
                )

    else:
        st.info("No category budgets saved for this month yet.")

except mysql.connector.Error as error:
    st.error(f"Could not load category budgets: {error}")


st.divider()


# --------------------------------------------------
# MONTH-BY-MONTH EXPENSE HISTORY
# --------------------------------------------------

st.header("📅 Month-by-Month Spending History")

if expenses_df.empty:
    st.info("Add expenses to see monthly history.")

else:
    history_df = expenses_df.copy()

    history_df["month"] = pd.to_datetime(
        history_df["expense_date"]
    ).dt.to_period("M")

    this_month = pd.Period(today, freq="M")

    first_month = min(history_df["month"].min(), this_month)
    last_month = max(history_df["month"].max(), this_month)

    all_months = pd.period_range(
        first_month,
        last_month,
        freq="M",
    )

    monthly_totals = (
        history_df.groupby("month")["amount"]
        .sum()
        .reindex(all_months, fill_value=0.0)
    )

    chart_df = pd.DataFrame(
        {
            "Month": [
                month.strftime("%b %Y")
                for month in all_months
            ],
            "Spent (₹)": monthly_totals.to_numpy(),
        }
    )

    st.bar_chart(
        chart_df,
        x="Month",
        y="Spent (₹)",
    )

    selected_month = st.selectbox(
        "Choose a month",
        options=list(reversed(all_months)),
        format_func=lambda month: month.strftime("%B %Y"),
    )

    selected_total = float(monthly_totals.loc[selected_month])

    previous_total = float(
        monthly_totals.get(selected_month - 1, 0.0)
    )

    change = selected_total - previous_total

    history_col1, history_col2, history_col3 = st.columns(3)

    history_col1.metric(
        "Selected month",
        f"₹{selected_total:,.2f}",
    )

    history_col2.metric(
        "Previous month",
        f"₹{previous_total:,.2f}",
    )

    history_col3.metric(
        "Difference",
        f"₹{change:+,.2f}",
    )

    selected_expenses = history_df[
        history_df["month"] == selected_month
    ]

    if selected_expenses.empty:
        st.info("No expenses recorded for this month.")

    else:
        st.subheader("Category breakdown")

        selected_categories = (
            selected_expenses.groupby(
                "category",
                as_index=False,
            )["amount"]
            .sum()
            .rename(
                columns={
                    "category": "Category",
                    "amount": "Spent (₹)",
                }
            )
        )

        st.dataframe(
            selected_categories,
            hide_index=True,
            use_container_width=True,
        )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()
st.caption("Smart Expense Tracker | Built with Python, Streamlit and MySQL")