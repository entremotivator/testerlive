import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

st.sidebar.image("logooo.png", use_column_width=True)

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("You need to log in to access this page.")
    st.stop()
    
# Generate sample data
def generate_sample_data():
    np.random.seed(42)
    dates = pd.date_range(start="2014-01-01", periods=120, freq='M')  # 10 years of monthly data
    
    # Extended and diversified data
    data = {
        "Date": dates,
        "Credit Score": np.random.randint(650, 850, size=120),
        "Credit Utilization": np.random.uniform(0.2, 0.9, size=120),
        "Total Debt": np.random.randint(1000, 20000, size=120),
        "Monthly Payments": np.random.randint(100, 2000, size=120),
        "Income": np.random.randint(3000, 10000, size=120),
        "New Credit Accounts": np.random.randint(0, 5, size=120),
        "Credit Limits": np.random.randint(5000, 50000, size=120),
        "Payment History": np.random.choice(["On Time", "Late"], size=120, p=[0.85, 0.15]),
        "Loan Balances": np.random.randint(1000, 20000, size=120),
        "Account Age (Months)": np.random.randint(1, 180, size=120),
        "Recent Transactions": np.random.randint(0, 20, size=120),
        "Upcoming Payments": np.random.randint(50, 2000, size=120),
        "Credit Inquiries": np.random.randint(0, 10, size=120),
        "Credit Report Summary": np.random.choice(["Excellent", "Good", "Average", "Poor"], size=120),
        "Credit Account Type": np.random.choice(["Credit Card", "Loan", "Mortgage", "Auto Loan"], size=120),
        "Interest Rate": np.random.uniform(2.5, 18.0, size=120),
        "Total Payments": np.random.uniform(1000, 20000, size=120),
        "Credit Utilization Trend": np.random.uniform(0.1, 0.8, size=120),
    }
    
    df = pd.DataFrame(data)
    df["Debt-to-Income Ratio"] = df["Total Debt"] / df["Income"]
    
    # Introduce some variability in interest rates and credit account types over time
    df.loc[df['Credit Account Type'] == 'Credit Card', 'Interest Rate'] = np.random.uniform(10, 18.0, size=df[df['Credit Account Type'] == 'Credit Card'].shape[0])
    df.loc[df['Credit Account Type'] == 'Loan', 'Interest Rate'] = np.random.uniform(3, 10, size=df[df['Credit Account Type'] == 'Loan'].shape[0])
    df.loc[df['Credit Account Type'] == 'Mortgage', 'Interest Rate'] = np.random.uniform(2.5, 5, size=df[df['Credit Account Type'] == 'Mortgage'].shape[0])
    df.loc[df['Credit Account Type'] == 'Auto Loan', 'Interest Rate'] = np.random.uniform(4, 12, size=df[df['Credit Account Type'] == 'Auto Loan'].shape[0])
    
    return df

df = generate_sample_data()

# Streamlit app
st.title("Credit Management Dashboard")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", [
    "Credit Score Overview",
    "Credit Utilization",
    "Payment History",
    "Credit Report Summary",
    "Credit Inquiries",
    "Credit Limits",
    "Debt-to-Income Ratio",
    "Loan and Credit Card Balances",
    "Account Age",
    "Monthly Payments",
    "Credit Accounts Breakdown",
    "Top 5 Highest Balances",
    "Top 5 Recent Transactions",
    "Upcoming Payments",
    "Credit Utilization by Account Type",
    "Average Payment History",
    "Credit Score Trend",
    "Monthly Spending Trend",
    "Credit Score vs. Credit Utilization",
    "Debt Repayment Schedule",
    "New Credit Accounts",
    "Credit Score Impact Simulation",
    "Debt Reduction Plan",
    "Credit Score Improvement Tips",
    "Alerts and Recommendations",
    "Edit Credit Info",
    "Export Data"
])

# Display selected page
if page == "Credit Score Overview":
    st.subheader("Credit Score Overview")
    st.write(f"Current Credit Score: {df['Credit Score'].iloc[-1]}")
    st.line_chart(df[['Date', 'Credit Score']].set_index('Date'))
    
    # Detailed Analysis
    trend = "increasing" if df['Credit Score'].pct_change().mean() > 0 else "decreasing"
    st.write(f"Overall trend: {trend}")
    st.write("Ensure your credit score remains in good health by following the improvement tips on the relevant page.")
    st.write("### Insights:")
    st.write("A higher credit score generally reflects a better credit history and lower credit risk.")

elif page == "Credit Utilization":
    st.subheader("Credit Utilization")
    st.bar_chart(df[['Date', 'Credit Utilization']].set_index('Date'))
    
    # Utilization Analysis
    avg_utilization = df['Credit Utilization'].mean()
    st.write(f"Average Credit Utilization: {avg_utilization:.2%}")
    st.write("A utilization rate below 30% is generally recommended.")
    st.write("### Insights:")
    st.write("Keeping your credit utilization low can positively impact your credit score.")

elif page == "Payment History":
    st.subheader("Payment History")
    st.write(df[['Date', 'Payment History']].set_index('Date'))
    
    # Payment History Analysis
    late_payments = df[df['Payment History'] == "Late"].shape[0]
    st.write(f"Number of Late Payments: {late_payments}")
    st.write("### Insights:")
    st.write("Timely payments are crucial for maintaining a good credit score. Address any late payments promptly.")

elif page == "Credit Report Summary":
    st.subheader("Credit Report Summary")
    summary_counts = df['Credit Report Summary'].value_counts()
    st.bar_chart(summary_counts)
    st.write("Review your credit report summary for a quick overview of your credit standing.")
    st.write("### Insights:")
    st.write("A good credit report summary indicates strong credit health.")

elif page == "Credit Inquiries":
    st.subheader("Credit Inquiries")
    st.line_chart(df[['Date', 'Credit Inquiries']].set_index('Date'))
    
    # Detailed Analysis
    total_inquiries = df['Credit Inquiries'].sum()
    st.write(f"Total Credit Inquiries: {total_inquiries}")
    st.write("### Insights:")
    st.write("Frequent credit inquiries can negatively affect your credit score. Limit new credit applications.")

elif page == "Credit Limits":
    st.subheader("Credit Limits")
    st.line_chart(df[['Date', 'Credit Limits']].set_index('Date'))
    st.write("### Insights:")
    st.write("Higher credit limits can improve your credit utilization ratio if managed responsibly.")

elif page == "Debt-to-Income Ratio":
    st.subheader("Debt-to-Income Ratio")
    st.line_chart(df[['Date', 'Debt-to-Income Ratio']].set_index('Date'))
    
    # Ratio Interpretation
    st.write("A lower debt-to-income ratio indicates better financial health.")
    high_ratio = df['Debt-to-Income Ratio'].max()
    st.write(f"Highest Recorded Ratio: {high_ratio:.2%}")
    st.write("### Insights:")
    st.write("Maintaining a low debt-to-income ratio is essential for financial stability.")

elif page == "Loan and Credit Card Balances":
    st.subheader("Loan and Credit Card Balances")
    st.line_chart(df[['Date', 'Loan Balances']].set_index('Date'))
    st.write("### Insights:")
    st.write("Regularly review your loan and credit card balances to manage debts effectively.")

elif page == "Account Age":
    st.subheader("Account Age")
    st.line_chart(df[['Date', 'Account Age (Months)']].set_index('Date'))
    st.write("### Insights:")
    st.write("A longer account age generally contributes to a better credit score by demonstrating a stable credit history.")

elif page == "Monthly Payments":
    st.subheader("Monthly Payments")
    st.line_chart(df[['Date', 'Monthly Payments']].set_index('Date'))
    st.write("### Insights:")
    st.write("Track your monthly payments to ensure you stay within your budget and avoid missed payments.")

elif page == "Credit Accounts Breakdown":
    st.subheader("Credit Accounts Breakdown")
    account_types = df['Credit Report Summary'].value_counts()
    st.bar_chart(account_types)
    st.write("### Insights:")
    st.write("Understanding the breakdown of your credit accounts helps in managing and optimizing your credit profile.")

elif page == "Top 5 Highest Balances":
    st.subheader("Top 5 Highest Balances")
    top_balances = df.nlargest(5, 'Loan Balances')
    st.write(top_balances[['Date', 'Loan Balances']])
    st.write("### Insights:")
    st.write("Identify and manage accounts with the highest balances to reduce your overall debt burden.")

elif page == "Top 5 Recent Transactions":
    st.subheader("Top 5 Recent Transactions")
    top_transactions = df.nlargest(5, 'Recent Transactions')
    st.write(top_transactions[['Date', 'Recent Transactions']])
    st.write("### Insights:")
    st.write("Monitoring recent transactions can help in understanding spending patterns and adjusting budgeting strategies.")

elif page == "Upcoming Payments":
    st.subheader("Upcoming Payments")
    st.line_chart(df[['Date', 'Upcoming Payments']].set_index('Date'))
    st.write("### Insights:")
    st.write("Plan for upcoming payments to avoid late fees and manage your finances efficiently.")

elif page == "Credit Utilization by Account Type":
    st.subheader("Credit Utilization by Account Type")
    account_types = ['Credit Card', 'Loan', 'Mortgage']
    utilization_by_type = df.groupby('Credit Report Summary')['Credit Utilization'].mean()
    st.bar_chart(utilization_by_type)
    st.write("### Insights:")
    st.write("Analyze credit utilization by account type to understand how different types of credit impact your overall utilization.")

elif page == "Average Payment History":
    st.subheader("Average Payment History")
    payment_history_avg = df['Payment History'].value_counts(normalize=True) * 100
    st.bar_chart(payment_history_avg)
    st.write("### Insights:")
    st.write("Maintaining an average of timely payments is crucial for a positive credit history.")

elif page == "Credit Score Trend":
    st.subheader("Credit Score Trend")
    st.line_chart(df[['Date', 'Credit Score']].set_index('Date'))
    st.write("### Insights:")
    st.write("A trend line helps visualize improvements or declines in your credit score over time.")

elif page == "Monthly Spending Trend":
    st.subheader("Monthly Spending Trend")
    st.line_chart(df[['Date', 'Monthly Payments']].set_index('Date'))
    st.write("### Insights:")
    st.write("Monitor monthly spending to ensure you stay within budget and avoid unnecessary debt.")

elif page == "Credit Score vs. Credit Utilization":
    st.subheader("Credit Score vs. Credit Utilization")
    fig = px.scatter(df, x='Credit Utilization', y='Credit Score', trendline='ols')
    st.plotly_chart(fig)
    st.write("### Insights:")
    st.write("Visualizing the relationship between credit utilization and credit score can help in understanding their correlation.")

elif page == "Debt Repayment Schedule":
    st.subheader("Debt Repayment Schedule")
    st.write("Create a repayment schedule to track and manage your debt reduction plans.")
    # Simulated example
    repayment_schedule = {
        "Debt Type": ["Credit Card", "Loan", "Mortgage"],
        "Current Balance": [5000, 15000, 200000],
        "Monthly Payment": [100, 300, 1500],
        "Remaining Months": [50, 60, 180]
    }
    repayment_df = pd.DataFrame(repayment_schedule)
    st.write(repayment_df)
    st.write("### Insights:")
    st.write("Effective debt repayment scheduling can help you achieve financial goals and reduce overall debt.")

elif page == "New Credit Accounts":
    st.subheader("New Credit Accounts")
    st.bar_chart(df[['Date', 'New Credit Accounts']].set_index('Date'))
    st.write("### Insights:")
    st.write("Monitor new credit accounts to ensure that they are managed well and do not negatively impact your credit score.")

elif page == "Credit Score Impact Simulation":
    st.subheader("Credit Score Impact Simulation")
    st.write("Simulate how changes in your credit behavior could impact your credit score.")
    # Interactive simulation
    score_change = st.slider("Projected Credit Score Change", min_value=-100, max_value=100, value=0)
    projected_score = df['Credit Score'].iloc[-1] + score_change
    st.write(f"Projected Credit Score: {projected_score}")
    st.write("### Insights:")
    st.write("Understand how different scenarios affect your credit score to make informed financial decisions.")

elif page == "Debt Reduction Plan":
    st.subheader("Debt Reduction Plan")
    st.write("Plan and track your progress in reducing debt.")
    # Sample debt reduction plan
    reduction_plan = {
        "Debt Type": ["Credit Card", "Loan", "Mortgage"],
        "Current Balance": [5000, 15000, 200000],
        "Monthly Payment": [100, 300, 1500],
        "Debt Reduction Plan": ["Pay Extra", "Consolidate", "Refinance"]
    }
    plan_df = pd.DataFrame(reduction_plan)
    st.write(plan_df)
    st.write("### Insights:")
    st.write("Effective debt reduction strategies can improve your financial health and credit score.")

elif page == "Credit Score Improvement Tips":
    st.subheader("Credit Score Improvement Tips")
    st.write("""
        **1. Pay Bills On Time:** Timely payments are crucial for a healthy credit score.
        **2. Reduce Credit Utilization:** Keep your credit utilization below 30% of your credit limit.
        **3. Avoid Opening Too Many Accounts:** Each credit inquiry can lower your score temporarily.
        **4. Regularly Check Your Credit Report:** Ensure there are no errors that might negatively affect your score.
        **5. Maintain a Healthy Credit Mix:** Having a mix of credit types (e.g., credit cards, loans) can be beneficial.
    """)

elif page == "Alerts and Recommendations":
    st.subheader("Alerts and Recommendations")
    st.write("Based on your data, here are some alerts and recommendations:")
    if df['Credit Utilization'].iloc[-1] > 0.3:
        st.warning("Your credit utilization is high. Consider paying down your balances.")
    if df['Payment History'].iloc[-1] == "Late":
        st.warning("You have recent late payments. Ensure you pay on time to avoid further impacts.")
    
elif page == "Edit Credit Info":
    st.subheader("Edit Credit Information")
    st.write("Update your credit data directly.")
    
    # Forms for editing
    with st.form(key='edit_form'):
        date_index = st.number_input("Select Date Index", min_value=0, max_value=len(df)-1, value=0)
        credit_score = st.number_input("Credit Score", min_value=300, max_value=850, value=int(df.loc[date_index, 'Credit Score']))
        credit_utilization = st.slider("Credit Utilization", min_value=0.0, max_value=1.0, value=df.loc[date_index, 'Credit Utilization'])
        total_debt = st.number_input("Total Debt", min_value=0, max_value=100000, value=int(df.loc[date_index, 'Total Debt']))
        income = st.number_input("Income", min_value=0, max_value=100000, value=int(df.loc[date_index, 'Income']))
        monthly_payments = st.number_input("Monthly Payments", min_value=0, max_value=10000, value=int(df.loc[date_index, 'Monthly Payments']))
        new_credit_accounts = st.number_input("New Credit Accounts", min_value=0, max_value=10, value=int(df.loc[date_index, 'New Credit Accounts']))
        credit_limits = st.number_input("Credit Limits", min_value=5000, max_value=20000, value=int(df.loc[date_index, 'Credit Limits']))
        payment_history = st.selectbox("Payment History", ["On Time", "Late"], index=0 if df.loc[date_index, 'Payment History'] == "On Time" else 1)
        
        submit_button = st.form_submit_button(label='Update Information')
        
        if submit_button:
            df.loc[date_index, 'Credit Score'] = credit_score
            df.loc[date_index, 'Credit Utilization'] = credit_utilization
            df.loc[date_index, 'Total Debt'] = total_debt
            df.loc[date_index, 'Income'] = income
            df.loc[date_index, 'Monthly Payments'] = monthly_payments
            df.loc[date_index, 'New Credit Accounts'] = new_credit_accounts
            df.loc[date_index, 'Credit Limits'] = credit_limits
            df.loc[date_index, 'Payment History'] = payment_history
            df.loc[date_index, 'Debt-to-Income Ratio'] = total_debt / income if income != 0 else 0
            st.success(f"Information updated for {df.loc[date_index, 'Date']}")

elif page == "Export Data":
    st.subheader("Export Data")
    st.write("Download your credit data in CSV format.")
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name='credit_data.csv',
        mime='text/csv'
    )
