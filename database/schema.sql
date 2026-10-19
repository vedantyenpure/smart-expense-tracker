-- Smart Expense Tracker
-- Database schema reference

CREATE TABLE IF NOT EXISTS income (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amount DECIMAL(10, 2) NOT NULL,
    source VARCHAR(255) NOT NULL,
    income_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS expenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amount DECIMAL(10, 2) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    expense_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS monthly_budgets (
    budget_month CHAR(7) NOT NULL PRIMARY KEY,
    budget_amount DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS category_budgets (
    budget_month CHAR(7) NOT NULL,
    category VARCHAR(100) NOT NULL,
    budget_amount DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (budget_month, category)
);