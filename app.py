from datetime import date
from decimal import Decimal

import mysql.connector
import pandas as pd
import streamlit as st

from db import get_connection


st.title("💰 Smart Expense Tracker")

with st.form("add_expense"):
    st.subheader("Add an expense")

    amount = st.number_input("Amount (₹)", min_value=0.01, step=1.0)
    category = st.selectbox(
        "Category",
        ["Food", "Travel", "Shopping", "Bills", "Health", "Other"],
    )
    description = st.text_input("Description (optional)")
    expense_date = st.date_input("Date", value=date.today())

    submitted = st.form_submit_button("Save expense")

if submitted:
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO expenses (amount, category, description, expense_date)
            VALUES (%s, %s, %s, %s)
            """,
            (
                Decimal(str(amount)),
                category,
                description.strip() or None,
                expense_date,
            ),
        )
        connection.commit()
        st.success("Expense saved! ✅")
    except mysql.connector.Error as error:
        st.error(f"Could not save expense: {error}")
    finally:
        if connection and connection.is_connected():
            connection.close()

st.subheader("Add income")

with st.form("add_income"):
    income_amount = st.number_input(
        "Income amount (₹)",
        min_value=0.01,
        step=100.0,
    )
    income_source = st.text_input(
        "Income source",
        placeholder="e.g. Salary, freelance work",
    )
    income_date = st.date_input(
        "Income date",
        value=date.today(),
    )
    income_submitted = st.form_submit_button("Save income")

income_connection = None

try:
    income_connection = get_connection()
    income_cursor = income_connection.cursor()

    if income_submitted:
        if not income_source.strip():
            st.warning("Enter an income source before saving.")
        else:
            income_cursor.execute(
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
            income_connection.commit()
            st.success("Income saved! ✅")

    # First day of this month and first day of next month.
    month_start = date.today().replace(day=1)
    if month_start.month == 12:
        next_month_start = date(month_start.year + 1, 1, 1)
    else:
        next_month_start = date(
            month_start.year,
            month_start.month + 1,
            1,
        )

    income_cursor.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM income
        WHERE income_date >= %s AND income_date < %s
        """,
        (month_start, next_month_start),
    )
    monthly_income = float(income_cursor.fetchone()[0])

    income_cursor.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE expense_date >= %s AND expense_date < %s
        """,
        (month_start, next_month_start),
    )
    monthly_spending = float(income_cursor.fetchone()[0])

    monthly_balance = monthly_income - monthly_spending

    st.subheader("This month's balance")
    col1, col2, col3 = st.columns(3)
    col1.metric("Income", f"₹{monthly_income:,.2f}")
    col2.metric("Expenses", f"₹{monthly_spending:,.2f}")
    col3.metric("Balance", f"₹{monthly_balance:,.2f}")

    if monthly_balance < 0:
        st.warning(
            f"Expenses exceed income by ₹{abs(monthly_balance):,.2f} "
            "this month."
        )

except mysql.connector.Error as error:
    st.error(f"Could not load or save income: {error}")
finally:
    if income_connection and income_connection.is_connected():
        income_connection.close()

st.subheader("Your expenses")

connection = None
try:
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, expense_date, category, description, amount
        FROM expenses
        ORDER BY expense_date DESC, id DESC
        """
    )
    expenses = cursor.fetchall()

    if expenses:
        df = pd.DataFrame(expenses)
        df["amount"] = df["amount"].astype(float)
        st.metric("Total expenses", f"₹{df['amount'].sum():,.2f}")
        st.dataframe(df)

        st.subheader("Edit or delete an expense")

        # Show a message after the page refreshes following an update/delete.
        notice = st.session_state.pop("expense_notice", None)
        if notice:
            st.success(notice)

        expenses_by_id = {int(item["id"]): item for item in expenses}

        selected_id = st.selectbox(
            "Choose an expense",
            options=list(expenses_by_id.keys()),
            format_func=lambda expense_id: (
                f"#{expense_id} — "
                f"{expenses_by_id[expense_id]['expense_date']} — "
                f"{expenses_by_id[expense_id]['category']} — "
                f"₹{float(expenses_by_id[expense_id]['amount']):,.2f}"
            ),
        )
        selected = expenses_by_id[selected_id]

        categories = ["Food", "Travel", "Shopping", "Bills", "Health", "Other"]

        with st.form("edit_expense_form"):
            st.write("**Edit selected expense**")

            edit_amount = st.number_input(
                "Amount (₹)",
                min_value=0.01,
                value=float(selected["amount"]),
                step=1.0,
            )
            edit_category = st.selectbox(
                "Category",
                categories,
                index=categories.index(selected["category"]),
            )
            edit_description = st.text_input(
                "Description",
                value=selected["description"] or "",
            )
            edit_date = st.date_input(
                "Date",
                value=pd.to_datetime(selected["expense_date"]).date(),
            )

            update_clicked = st.form_submit_button("Update expense")

        if update_clicked:
            edit_connection = None
            try:
                edit_connection = get_connection()
                edit_cursor = edit_connection.cursor()
                edit_cursor.execute(
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
                edit_connection.commit()
                st.session_state["expense_notice"] = "Expense updated! ✅"
                st.rerun()
            except mysql.connector.Error as error:
                st.error(f"Could not update expense: {error}")
            finally:
                if edit_connection and edit_connection.is_connected():
                    edit_connection.close()

        with st.form("delete_expense_form"):
            st.write("**Delete selected expense**")
            confirm_delete = st.checkbox(
                "I understand this expense will be permanently deleted"
            )
            delete_clicked = st.form_submit_button("Delete expense")

        if delete_clicked:
            if not confirm_delete:
                st.warning("Tick the confirmation box before deleting.")
            else:
                delete_connection = None
                try:
                    delete_connection = get_connection()
                    delete_cursor = delete_connection.cursor()
                    delete_cursor.execute(
                        "DELETE FROM expenses WHERE id = %s",
                        (selected_id,),
                    )
                    delete_connection.commit()
                    st.session_state["expense_notice"] = "Expense deleted! ✅"
                    st.rerun()
                except mysql.connector.Error as error:
                    st.error(f"Could not delete expense: {error}")
                finally:
                    if delete_connection and delete_connection.is_connected():
                        delete_connection.close()
                        st.subheader("Find expenses")

        filter_df = df.copy()
        filter_df["expense_date"] = pd.to_datetime(filter_df["expense_date"])

        category_options = ["All"] + sorted(
            filter_df["category"].dropna().unique().tolist()
        )
        chosen_category = st.selectbox(
            "Filter by category",
            category_options,
            key="expense_category_filter",
        )

        search_text = st.text_input(
            "Search descriptions",
            placeholder="e.g. groceries",
            key="expense_description_search",
        )

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "From date",
                value=filter_df["expense_date"].min().date(),
                key="expense_filter_start",
            )
        with col2:
            end_date = st.date_input(
                "To date",
                value=filter_df["expense_date"].max().date(),
                key="expense_filter_end",
            )

        if start_date > end_date:
            st.warning("'From date' must be on or before 'To date'.")
        else:
            filtered_df = filter_df[
                filter_df["expense_date"].dt.date.between(
                    start_date, end_date
                )
            ].copy()

            if chosen_category != "All":
                filtered_df = filtered_df[
                    filtered_df["category"] == chosen_category
                ]

            if search_text.strip():
                filtered_df = filtered_df[
                    filtered_df["description"]
                    .fillna("")
                    .str.contains(search_text.strip(), case=False, regex=False)
                ]

            st.write(f"**{len(filtered_df)} expense(s) found**")
            st.metric(
                "Total of filtered expenses",
                f"₹{filtered_df['amount'].sum():,.2f}",
            )

            if filtered_df.empty:
                st.info("No expenses match these filters.")
            else:
                export_df = filtered_df[
                    ["expense_date", "category", "description", "amount"]
                ].copy()
                export_df["expense_date"] = export_df[
                    "expense_date"
                ].dt.strftime("%Y-%m-%d")

                st.dataframe(export_df, hide_index=True)

                st.download_button(
                    "Download these expenses as CSV",
                    data=export_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name="expenses.csv",
                    mime="text/csv",
                )
         

        st.subheader("Spending by category")
        category_totals = df.groupby("category", as_index=False)["amount"].sum()
        st.bar_chart(category_totals, x="category", y="amount")
        current_month = date.today().strftime("%Y-%m")
        st.subheader(f"Monthly budget — {current_month}")

        budget_connection = None
        try:
            budget_connection = get_connection()
            budget_cursor = budget_connection.cursor()

            budget_cursor.execute(
                "SELECT budget_amount FROM monthly_budgets WHERE budget_month = %s",
                (current_month,),
            )
            row = budget_cursor.fetchone()
            saved_budget = float(row[0]) if row else None

            budget_input = st.number_input(
                "Set monthly budget (₹)",
                min_value=1.0,
                value=saved_budget if saved_budget is not None else 1000.0,
                step=100.0,
            )

            if st.button("Save budget"):
                budget_cursor.execute(
                    """
                    INSERT INTO monthly_budgets (budget_month, budget_amount)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE budget_amount = %s
                    """,
                    (
                        current_month,
                        Decimal(str(budget_input)),
                        Decimal(str(budget_input)),
                    ),
                )
                budget_connection.commit()
                saved_budget = budget_input
                st.success("Budget saved! ✅")

            month_expenses = df[
                pd.to_datetime(df["expense_date"]).dt.strftime("%Y-%m")
                == current_month
            ]
            month_total = month_expenses["amount"].sum()
            st.metric("This month's spending", f"₹{month_total:,.2f}")

            if saved_budget is not None:
                if month_total > saved_budget:
                    st.warning(f"Budget exceeded by ₹{month_total - saved_budget:,.2f}!")
                else:
                    st.success(f"₹{saved_budget - month_total:,.2f} left in your budget.")

        except mysql.connector.Error as error:
            st.error(f"Could not load or save budget: {error}")
        finally:
            if budget_connection and budget_connection.is_connected():
                budget_connection.close()
             # Month-by-month spending history
            st.subheader("Category budgets")

        category_budget_connection = None
        try:
            category_budget_connection = get_connection()
            category_budget_cursor = category_budget_connection.cursor()

            budget_categories = [
                "Food", "Travel", "Shopping", "Bills", "Health", "Other"
            ]

            with st.form("category_budget_form"):
                budget_category = st.selectbox(
                    "Category to budget",
                    budget_categories,
                )
                category_limit = st.number_input(
                    "Monthly category limit (₹)",
                    min_value=1.0,
                    step=100.0,
                )
                save_category_budget = st.form_submit_button(
                    "Save category budget"
                )

            if save_category_budget:
                category_budget_cursor.execute(
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
                category_budget_connection.commit()
                st.success(f"{budget_category} budget saved! ✅")

            category_budget_cursor.execute(
                """
                SELECT category, budget_amount
                FROM category_budgets
                WHERE budget_month = %s
                """,
                (current_month,),
            )
            limits = {
                category_name: float(limit)
                for category_name, limit in category_budget_cursor.fetchall()
            }

            # Calculate this month's spending directly from saved expenses.
            category_month_df = df[
                pd.to_datetime(df["expense_date"]).dt.strftime("%Y-%m")
                == current_month
            ]
            spent_by_category = (
                category_month_df.groupby("category")["amount"]
                .sum()
                .to_dict()
            )

            if not limits:
                st.info("Set a category budget above to see comparisons.")
            else:
                budget_rows = []

                for category_name in budget_categories:
                    if category_name not in limits:
                        continue

                    limit = limits[category_name]
                    spent = float(spent_by_category.get(category_name, 0))
                    remaining = limit - spent

                    budget_rows.append({
                        "Category": category_name,
                        "Budget (₹)": limit,
                        "Spent (₹)": spent,
                        "Remaining (₹)": remaining,
                    })

                    if remaining < 0:
                        st.warning(
                            f"{category_name} is ₹{abs(remaining):,.2f} "
                            "over its category budget!"
                        )

                st.dataframe(
                    pd.DataFrame(budget_rows),
                    hide_index=True,
                    use_container_width=True,
                )

        except mysql.connector.Error as error:
            st.error(f"Could not load or save category budgets: {error}")
        finally:
            if (
                category_budget_connection
                and category_budget_connection.is_connected()
            ):
                category_budget_connection.close()

        st.subheader("Month-by-month history")

        history_df = df.copy()
        history_df["month"] = pd.to_datetime(
            history_df["expense_date"]
        ).dt.to_period("M")

        this_month = pd.Period(date.today(), freq="M")
        first_month = min(history_df["month"].min(), this_month)
        last_month = max(history_df["month"].max(), this_month)
        all_months = pd.period_range(first_month, last_month, freq="M")

        monthly_totals = (
            history_df.groupby("month")["amount"]
            .sum()
            .reindex(all_months, fill_value=0.0)
        )

        chart_df = pd.DataFrame({
            "Month": [month.strftime("%b %Y") for month in all_months],
            "Spent (₹)": monthly_totals.to_numpy(),
        })
        st.bar_chart(chart_df, x="Month", y="Spent (₹)")

        selected_month = st.selectbox(
            "View a month",
            options=list(reversed(all_months)),
            format_func=lambda month: month.strftime("%B %Y"),
        )

        selected_total = float(monthly_totals.loc[selected_month])
        previous_total = float(monthly_totals.get(selected_month - 1, 0.0))
        change = selected_total - previous_total

        col1, col2, col3 = st.columns(3)
        col1.metric("Selected month", f"₹{selected_total:,.2f}")
        col2.metric("Previous month", f"₹{previous_total:,.2f}")
        col3.metric("Change", f"{change:+,.2f} ₹")

        selected_expenses = history_df[
            history_df["month"] == selected_month
        ]

        if selected_expenses.empty:
            st.info("No expenses recorded for this month.")
        else:
            st.write("**Categories this month**")
            selected_categories = (
                selected_expenses.groupby("category", as_index=False)["amount"]
                .sum()
                .rename(columns={
                    "category": "Category",
                    "amount": "Spent (₹)",
                })
            )
            st.dataframe(
                selected_categories,
                hide_index=True,
                use_container_width=True,
            )








    else:
        st.info("No expenses yet. Add your first one above!")

except mysql.connector.Error as error:
    st.error(f"Could not load expenses: {error}")
finally:
    if connection and connection.is_connected():
        connection.close()
