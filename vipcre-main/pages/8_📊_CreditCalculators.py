import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.sidebar.image("logooo.png", use_column_width=True)

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("You need to log in to access this page.")
    st.stop()
    
# Function to calculate total amount payable for a credit card
def calculate_total_payment(balance, annual_rate, months):
    logger.info("Calculating total payment for credit card")
    monthly_rate = annual_rate / 100 / 12
    total_payment = balance * (1 + monthly_rate) ** months
    return total_payment

# Function to calculate the full payment schedule for a credit card
def calculate_credit_card_schedule(balance, annual_rate, months):
    logger.info("Calculating credit card payment schedule")
    monthly_rate = annual_rate / 100 / 12
    monthly_payment = (balance * monthly_rate) / (1 - (1 + monthly_rate) ** -months)
    
    schedule = []
    total_payment = 0
    total_interest = 0
    cumulative_interest = 0
    cumulative_principal = 0

    for i in range(1, months + 1):
        interest_payment = balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        balance -= principal_payment
        total_payment += monthly_payment
        cumulative_interest += interest_payment
        cumulative_principal += principal_payment
        total_interest += interest_payment
        schedule.append({
            "Month": i,
            "Payment": monthly_payment,
            "Principal Payment": principal_payment,
            "Interest Payment": interest_payment,
            "Cumulative Interest": cumulative_interest,
            "Cumulative Principal": cumulative_principal,
            "Remaining Balance": max(balance, 0)
        })
        if balance <= 0:
            break

    df_schedule = pd.DataFrame(schedule)
    return df_schedule, total_payment, total_interest

# Function to calculate minimum credit card payment
def calculate_minimum_payment(balance, annual_rate, minimum_percentage):
    logger.info("Calculating minimum payment for credit card")
    monthly_rate = annual_rate / 100 / 12
    minimum_payment = balance * (minimum_percentage / 100)
    total_payment = 0
    months = 0
    while balance > 0:
        interest = balance * monthly_rate
        balance = balance + interest - minimum_payment
        total_payment += minimum_payment
        months += 1
        if balance < 0:
            total_payment += balance
            balance = 0
    return total_payment, months

# Function to calculate amortization schedule with down payment
def calculate_amortization_schedule(principal, annual_rate, months, down_payment):
    logger.info("Calculating amortization schedule")
    # Adjust principal for down payment
    loan_amount = principal - down_payment
    monthly_rate = annual_rate / 100 / 12
    monthly_payment = (loan_amount * monthly_rate) / (1 - (1 + monthly_rate) ** -months)
    
    schedule = []
    total_payment = 0
    cumulative_interest = 0
    cumulative_principal = 0

    for i in range(1, months + 1):
        interest_payment = loan_amount * monthly_rate
        principal_payment = monthly_payment - interest_payment
        loan_amount -= principal_payment
        total_payment += monthly_payment
        cumulative_interest += interest_payment
        cumulative_principal += principal_payment
        schedule.append({
            "Month": i,
            "Payment": monthly_payment,
            "Principal Payment": principal_payment,
            "Interest Payment": interest_payment,
            "Cumulative Interest": cumulative_interest,
            "Cumulative Principal": cumulative_principal,
            "Remaining Balance": max(loan_amount, 0)
        })
        if loan_amount <= 0:
            break

    df_schedule = pd.DataFrame(schedule)
    return df_schedule

# Streamlit UI
st.title("Comprehensive Financial Calculators")

# Sidebar for selecting calculator
calculator_type = st.sidebar.selectbox(
    "Choose Calculator",
    ["Credit Card Calculator", "Amortization Calculator", "Credit Card Minimum Payment Calculator"]
)

# Credit Card Calculator
if calculator_type == "Credit Card Calculator":
    st.header("Credit Card Calculator")

    # Input fields
    balance = st.number_input("Credit Card Balance ($)", min_value=0.0, step=100.0)
    annual_rate = st.number_input("Annual Interest Rate (%)", min_value=0.0, step=0.1)
    months = st.number_input("Months to Pay Off", min_value=1, step=1)

    # Calculate button
    if st.button("Calculate Payment Schedule"):
        if balance > 0 and annual_rate >= 0 and months > 0:
            try:
                schedule_df, total_payment, total_interest = calculate_credit_card_schedule(balance, annual_rate, months)
                st.write("Payment Schedule")
                st.dataframe(schedule_df)
                st.success(f"The total amount payable is ${total_payment:,.2f}")
                st.info(f"Total interest paid over the term is ${total_interest:,.2f}")

                # Visualize Payment Schedule
                fig, ax = plt.subplots(2, 1, figsize=(12, 10))
                
                # Principal vs Interest Payment
                sns.lineplot(data=schedule_df, x="Month", y="Principal Payment", ax=ax[0], label='Principal Payment', color='blue')
                sns.lineplot(data=schedule_df, x="Month", y="Interest Payment", ax=ax[0], label='Interest Payment', color='red')
                ax[0].set_xlabel('Month')
                ax[0].set_ylabel('Payment ($)')
                ax[0].set_title('Principal and Interest Payment Breakdown')
                ax[0].legend()

                # Remaining Balance and Cumulative Interest
                ax[1].plot(schedule_df["Month"], schedule_df["Remaining Balance"], label='Remaining Balance', color='green')
                ax[1].plot(schedule_df["Month"], schedule_df["Cumulative Interest"], label='Cumulative Interest', color='orange')
                ax[1].set_xlabel('Month')
                ax[1].set_ylabel('Amount ($)')
                ax[1].set_title('Remaining Balance and Cumulative Interest Over Time')
                ax[1].legend()

                st.pyplot(fig)

                # Export Option
                st.download_button(
                    label="Download Payment Schedule as CSV",
                    data=schedule_df.to_csv(index=False).encode('utf-8'),
                    file_name='credit_card_payment_schedule.csv',
                    mime='text/csv'
                )
            except Exception as e:
                logger.error("Error calculating credit card schedule", exc_info=True)
                st.error("An error occurred while calculating the payment schedule.")
        else:
            st.error("Please enter valid inputs. Balance and months must be greater than 0.")

    st.write("This calculator provides a detailed payment schedule for paying off your credit card balance, showing how much of each payment goes towards principal, interest, cumulative interest, and the remaining balance.")

# Amortization Calculator
elif calculator_type == "Amortization Calculator":
    st.header("Amortization Calculator")

    # Input fields
    principal = st.number_input("Loan Principal ($)", min_value=0.0, step=1000.0)
    down_payment = st.number_input("Down Payment ($)", min_value=0.0, step=100.0)
    annual_rate = st.number_input("Annual Interest Rate (%)", min_value=0.0, step=0.1)
    months = st.number_input("Loan Term (Months)", min_value=1, step=1)

    # Calculate button
    if st.button("Calculate Amortization Schedule"):
        if principal > 0 and annual_rate >= 0 and months > 0:
            try:
                schedule_df = calculate_amortization_schedule(principal, annual_rate, months, down_payment)
                st.write("Amortization Schedule")
                st.dataframe(schedule_df)

                # Total Payment
                total_payment = schedule_df["Payment"].sum()
                st.success(f"The total amount payable over the term is ${total_payment:,.2f}")

                # Visualize Amortization Schedule
                fig, ax = plt.subplots(2, 1, figsize=(10, 8))
                
                # Principal vs Interest Payment
                sns.lineplot(data=schedule_df, x="Month", y="Principal Payment", ax=ax[0], label='Principal Payment', color='blue')
                sns.lineplot(data=schedule_df, x="Month", y="Interest Payment", ax=ax[0], label='Interest Payment', color='red')
                ax[0].set_xlabel('Month')
                ax[0].set_ylabel('Payment ($)')
                ax[0].set_title('Principal and Interest Payment Breakdown')
                ax[0].legend()

                # Remaining Balance
                sns.lineplot(data=schedule_df, x="Month", y="Remaining Balance", ax=ax[1], color='green')
                ax[1].set_xlabel('Month')
                ax[1].set_ylabel('Remaining Balance ($)')
                ax[1].set_title('Remaining Balance Over Time')

                st.pyplot(fig)

                # Export Option
                st.download_button(
                    label="Download Amortization Schedule as CSV",
                    data=schedule_df.to_csv(index=False).encode('utf-8'),
                    file_name='amortization_schedule.csv',
                    mime='text/csv'
                )
            except Exception as e:
                logger.error("Error calculating amortization schedule", exc_info=True)
                st.error("An error occurred while calculating the amortization schedule.")
        else:
            st.error("Please enter valid inputs. Principal and months must be greater than 0.")

    st.write("This calculator provides an amortization schedule for your loan, showing principal and interest payments, cumulative amounts, and remaining balance over time.")

# Credit Card Minimum Payment Calculator
elif calculator_type == "Credit Card Minimum Payment Calculator":
    st.header("Credit Card Minimum Payment Calculator")

    # Input fields
    balance = st.number_input("Credit Card Balance ($)", min_value=0.0, step=100.0)
    annual_rate = st.number_input("Annual Interest Rate (%)", min_value=0.0, step=0.1)
    min_percentage = st.number_input("Minimum Payment Percentage (%)", min_value=0.0, step=0.1)

    # Calculate button
    if st.button("Calculate Minimum Payment"):
        if balance > 0 and annual_rate >= 0 and min_percentage > 0:
            try:
                total_payment, months = calculate_minimum_payment(balance, annual_rate, min_percentage)
                st.success(f"Total payment amount to pay off the balance is ${total_payment:,.2f} over {months} months.")
            except Exception as e:
                logger.error("Error calculating minimum payment", exc_info=True)
                st.error("An error occurred while calculating the minimum payment.")
        else:
            st.error("Please enter valid inputs. Balance and percentage must be greater than 0.")

    st.write("This calculator estimates the total amount you'll pay and the duration required to pay off your credit card balance based on the minimum payment percentage.")
