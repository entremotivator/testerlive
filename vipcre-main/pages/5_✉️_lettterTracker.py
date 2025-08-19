import streamlit as st
import pandas as pd
from datetime import datetime

# Set Streamlit to use the full width of the page
st.set_page_config(layout="wide")

st.sidebar.image("logooo.png", use_column_width=True)

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("You need to log in to access this page.")
    st.stop()
    
# Sample data to prepopulate the DataFrame with 10 clients
sample_data = {
    'Client Name': ['John Doe', 'Jane Smith', 'Michael Johnson', 'Emily Davis', 'Chris Brown', 
                    'Patricia Taylor', 'Robert Wilson', 'Linda Moore', 'James Anderson', 'Jennifer Lee'],
    'Letter Subject': ['Dispute Letter 1', 'Dispute Letter 2', 'Dispute Letter 3', 'Dispute Letter 4', 'Dispute Letter 5', 
                       'Dispute Letter 6', 'Dispute Letter 7', 'Dispute Letter 8', 'Dispute Letter 9', 'Dispute Letter 10'],
    'Date Sent': [datetime(2024, 8, 1), datetime(2024, 8, 2), datetime(2024, 8, 3), datetime(2024, 8, 4), datetime(2024, 8, 5),
                  datetime(2024, 8, 6), datetime(2024, 8, 7), datetime(2024, 8, 8), datetime(2024, 8, 9), datetime(2024, 8, 10)],
    'Status': ['Sent', 'In Review', 'Pending', 'Resolved', 'Sent', 'In Review', 'Pending', 'Resolved', 'Sent', 'Pending'],
    'To-Do List': ['Follow up in 2 weeks', 'Call client', 'Send additional documents', 'Review response', 'Prepare next letter',
                   'Update client on progress', 'Request more information', 'Prepare final report', 'Send follow-up email', 'Schedule review call'],
    'Notes': ['First letter sent', 'Requested additional info', 'Waiting for response', 'Resolved in favor of client', 'Letter sent, awaiting response',
              'Client requested more information', 'Additional documents needed', 'Final report prepared', 'Follow-up email sent', 'Review call scheduled'],
    'Dispute Type': ['Credit Report', 'Identity Theft', 'Fraudulent Account', 'Incorrect Info', 'Duplicate Account', 
                     'Credit Report', 'Identity Theft', 'Fraudulent Account', 'Incorrect Info', 'Duplicate Account'],
    'Credit Bureau': ['Experian', 'TransUnion', 'Equifax', 'Experian', 'TransUnion', 
                      'Equifax', 'Experian', 'TransUnion', 'Equifax', 'Experian'],
    'Priority': ['High', 'Medium', 'Low', 'High', 'Medium', 
                 'Low', 'High', 'Medium', 'Low', 'High']
}

# Initialize session state for the tracking DataFrame
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(sample_data)

# Function to add a new row (letter) to the DataFrame
def add_letter(client_name, letter_subject, date_sent, status, to_do_list, notes, dispute_type, credit_bureau, priority):
    new_row = {
        'Client Name': client_name,
        'Letter Subject': letter_subject,
        'Date Sent': date_sent,
        'Status': status,
        'To-Do List': to_do_list,
        'Notes': notes,
        'Dispute Type': dispute_type,
        'Credit Bureau': credit_bureau,
        'Priority': priority
    }
    st.session_state.df = st.session_state.df.append(new_row, ignore_index=True)

# Streamlit UI Components
st.title("Enhanced Credit Dispute Letter Tracker")

# Form to add a new letter and tasks
with st.form("add_letter_form"):
    st.header("Add New Letter & Tasks")
    client_name = st.text_input("Client Name")
    letter_subject = st.text_input("Letter Subject")
    date_sent = st.date_input("Date Sent")
    status = st.selectbox("Status", ["Sent", "In Review", "Resolved", "Pending"])
    to_do_list = st.text_area("To-Do List (Separate tasks with commas)")
    notes = st.text_area("Additional Notes")
    dispute_type = st.selectbox("Dispute Type", ["Credit Report", "Identity Theft", "Fraudulent Account", "Incorrect Info", "Duplicate Account"])
    credit_bureau = st.selectbox("Credit Bureau", ["Experian", "TransUnion", "Equifax"])
    priority = st.selectbox("Priority", ["High", "Medium", "Low"])
    
    if st.form_submit_button("Add Letter"):
        if client_name and letter_subject:
            add_letter(client_name, letter_subject, date_sent, status, to_do_list, notes, dispute_type, credit_bureau, priority)
            st.success("Letter and tasks added successfully!")

# Display the DataFrame in a full-screen mode
st.header("Tracking Table")
st.dataframe(st.session_state.df, use_container_width=True)

# Export data to CSV
st.header("Export Data")
csv = st.session_state.df.to_csv(index=False)
st.download_button(label="Download as CSV", data=csv, file_name='credit_dispute_tracking.csv', mime='text/csv')

# Import data from CSV
st.header("Import Data")
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.session_state.df = df
    st.success("Data imported successfully!")

# Display the DataFrame again after possible changes
st.header("Current Data Overview")
st.dataframe(st.session_state.df, use_container_width=True)

