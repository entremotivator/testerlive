import streamlit as st
import pandas as pd
import os

# Initialize Streamlit app
st.set_page_config(page_title="Credit Building Blueprint")

# Title and Subheader
st.title("**Credit Building Blueprint - 10 Key Projects**")
st.subheader("Organize and Manage Your Credit Building Projects Effectively!")
st.sidebar.image("logooo.png", use_column_width=True)

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("You need to log in to access this page.")
    st.stop()
    
# Local Database
@st.cache_data
def get_local_data():
    return pd.DataFrame(columns=["Title", "Steps"])

data = get_local_data()

# Functions for interacting with local data
def save_local_data():
    data.to_csv("credit_projects.csv", index=False)

def load_local_data():
    if "credit_projects.csv" in os.listdir():
        return pd.read_csv("credit_projects.csv")
    else:
        return pd.DataFrame(columns=["Title", "Steps"])

def add_title_steps(title, steps):
    global data
    new_entry = {"Title": title, "Steps": steps}
    data = data.append(new_entry, ignore_index=True)
    save_local_data()

def edit_title_steps(entry_id, updated_title, updated_steps):
    global data
    data.at[entry_id, "Title"] = updated_title
    data.at[entry_id, "Steps"] = updated_steps
    save_local_data()

def delete_entry(entry_id):
    global data
    data = data.drop(index=entry_id).reset_index(drop=True)
    save_local_data()

# Load data from CSV
data = load_local_data()

# Example Credit Building Projects and Steps
example_entries = [
    {
        "Title": "Review Credit Report",
        "Steps": [
            "Obtain a copy of your credit report from all three bureaus.",
            "Check for errors or inaccuracies.",
            "Dispute any inaccuracies with the credit bureaus.",
            "Review your credit history for trends.",
            "Understand your current credit score.",
            "Identify areas for improvement.",
            "Analyze any negative items impacting your score.",
            "Request updates or corrections to your credit history.",
            "Track changes to your credit report over time.",
            "Set goals for improving your credit score."
        ]
    },
    {
        "Title": "Pay Bills on Time",
        "Steps": [
            "Create a budget to manage expenses.",
            "Set up automatic payments or reminders.",
            "Prioritize paying bills before due dates.",
            "Monitor accounts regularly for missed payments.",
            "Adjust your budget as needed to ensure timely payments.",
            "Consider using a bill payment app for better tracking.",
            "Review your payment history for accuracy.",
            "Set up alerts for upcoming due dates.",
            "Plan for unexpected expenses to avoid late payments.",
            "Evaluate your payment methods and choose the most efficient ones."
        ]
    },
    {
        "Title": "Reduce Credit Card Balances",
        "Steps": [
            "List all credit card debts and their interest rates.",
            "Create a debt repayment plan.",
            "Focus on paying down high-interest cards first.",
            "Consider balance transfers to lower interest rates.",
            "Avoid adding new charges to paid-off cards.",
            "Make more than the minimum payment whenever possible.",
            "Set up a payment schedule to reduce balances gradually.",
            "Monitor your credit utilization ratio regularly.",
            "Seek advice on effective debt reduction strategies.",
            "Review and adjust your plan as needed."
        ]
    },
    {
        "Title": "Increase Credit Limit",
        "Steps": [
            "Contact your credit card issuer to request a limit increase.",
            "Provide financial information if requested.",
            "Maintain a good payment history before requesting.",
            "Use the increased limit responsibly.",
            "Monitor your credit utilization ratio with the new limit.",
            "Evaluate the impact of the limit increase on your credit score.",
            "Consider setting spending limits on your cards.",
            "Review your credit report for changes.",
            "Adjust your budget to reflect the new credit limit.",
            "Continue to manage your credit card balances effectively."
        ]
    },
    {
        "Title": "Open a Secured Credit Card",
        "Steps": [
            "Research secured credit cards with favorable terms.",
            "Apply for a secured card and deposit the required amount.",
            "Use the card for small purchases and pay off balances in full.",
            "Track your credit score for improvements.",
            "Consider transitioning to an unsecured card over time.",
            "Monitor the terms of the secured card for changes.",
            "Review your credit report to see the impact of the new card.",
            "Set up automatic payments to avoid missed payments.",
            "Evaluate other credit-building options.",
            "Plan for the transition from a secured to unsecured card."
        ]
    },
    {
        "Title": "Establish Credit History",
        "Steps": [
            "Apply for credit with a retailer or bank.",
            "Use the credit responsibly and make timely payments.",
            "Consider becoming an authorized user on someone else's account.",
            "Avoid applying for too much credit at once.",
            "Monitor your credit report regularly.",
            "Review your credit history for completeness.",
            "Maintain a positive credit utilization ratio.",
            "Set goals for credit account management.",
            "Evaluate the impact of new credit accounts on your score.",
            "Seek professional advice if needed."
        ]
    },
    {
        "Title": "Monitor Credit Regularly",
        "Steps": [
            "Sign up for a credit monitoring service.",
            "Set up alerts for any changes in your credit report.",
            "Review credit reports at least once a year.",
            "Address any issues or changes promptly.",
            "Track your credit score trends over time.",
            "Compare your credit score with industry benchmarks.",
            "Evaluate the effectiveness of your credit-building strategies.",
            "Update your credit monitoring service as needed.",
            "Review the terms of your monitoring service.",
            "Seek help if you notice any suspicious activity."
        ]
    },
    {
        "Title": "Negotiate with Creditors",
        "Steps": [
            "Identify accounts with high interest rates or fees.",
            "Contact creditors to negotiate better terms.",
            "Request lower interest rates or fee waivers.",
            "Document all agreements and changes.",
            "Follow up to ensure agreements are honored.",
            "Review your credit card statements for updated terms.",
            "Evaluate the impact of negotiated terms on your credit score.",
            "Set reminders to review and renegotiate terms if needed.",
            "Consider consolidating debts if beneficial.",
            "Seek professional assistance if negotiations are unsuccessful."
        ]
    },
    {
        "Title": "Build a Positive Credit Mix",
        "Steps": [
            "Maintain a mix of credit accounts (revolving and installment).",
            "Avoid closing old accounts, as they contribute to credit history length.",
            "Manage each type of credit responsibly.",
            "Monitor the impact of your credit mix on your score.",
            "Adjust your credit strategy to maintain a healthy mix.",
            "Consider diversifying your credit portfolio strategically.",
            "Review your credit mix regularly for balance.",
            "Set goals for maintaining a positive credit mix.",
            "Seek advice on managing different types of credit accounts.",
            "Evaluate the effects of new credit accounts on your mix."
        ]
    },
    {
        "Title": "Avoid New Hard Inquiries",
        "Steps": [
            "Limit the number of credit applications.",
            "Apply for credit only when necessary.",
            "Research credit options before applying.",
            "Monitor your credit report for hard inquiries.",
            "Understand the impact of hard inquiries on your score.",
            "Avoid multiple credit applications within a short period.",
            "Set goals for managing credit inquiries.",
            "Review the terms of each credit application before applying.",
            "Evaluate the benefits versus risks of new credit applications.",
            "Seek alternatives to traditional credit applications if needed."
        ]
    },
    {
        "Title": "Create a Credit Improvement Plan",
        "Steps": [
            "Set clear credit goals and objectives.",
            "Develop a step-by-step action plan.",
            "Track progress and adjust strategies as needed.",
            "Seek professional advice if necessary.",
            "Review and revise the plan regularly.",
            "Set up milestones to measure progress.",
            "Monitor the impact of each action on your credit score.",
            "Adjust your plan based on feedback and results.",
            "Stay informed about credit management best practices.",
            "Celebrate achievements and plan for future improvements."
        ]
    }
]

# Display Titles with Steps
for entry_id, entry_data in enumerate(example_entries):
    entry_key = f"title-{entry_id}"
    with st.expander(entry_data["Title"], expanded=False):
        st.write("### Steps:")
        for step in entry_data["Steps"]:
            st.write(f"- {step}")
        
        # Edit button and functionality
        if st.button("Edit", key=f"edit-{entry_id}"):
            updated_title = st.text_input("Title", value=entry_data["Title"])
            updated_steps = st.text_area("Steps (one per line)", value="\n".join(entry_data["Steps"]))
            if st.button("Save Changes", key=f"save-{entry_id}"):
                edit_title_steps(entry_id, updated_title, updated_steps.split("\n"))
                st.experimental_rerun()
        
        # Delete button and functionality
        if st.button("Delete", key=f"delete-{entry_id}"):
            delete_entry(entry_id)
            st.experimental_rerun()

# Functionality to add a new title with steps
with st.expander("Add New Project", expanded=False):
    title = st.text_input("New Title")
    steps = st.text_area("Steps (one per line)")
    if st.button("Add Project"):
        add_title_steps(title, steps.split("\n"))
        st.experimental_rerun()

st.write("### Credit Building Blueprint - Stay Organized and Achieve Your Goals!")
