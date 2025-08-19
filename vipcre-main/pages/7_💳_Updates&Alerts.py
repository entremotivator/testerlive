import streamlit as st
import pandas as pd
from datetime import datetime

st.sidebar.image("logooo.png", use_column_width=True)

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("You need to log in to access this page.")
    st.stop()
    
# Expanded sample data for messages
messages_data = [
    {"sender": "Client", "recipient": "Customer", "message": "Your credit report has been updated.", "timestamp": "2024-08-25 12:00"},
    {"sender": "Customer", "recipient": "Client", "message": "Thank you for the update.", "timestamp": "2024-08-25 13:00"},
    {"sender": "Client", "recipient": "Customer", "message": "Please review the recent credit inquiry.", "timestamp": "2024-08-24 10:30"},
    {"sender": "Customer", "recipient": "Client", "message": "The inquiry has been reviewed. No action needed.", "timestamp": "2024-08-24 11:00"},
    {"sender": "Client", "recipient": "Customer", "message": "Your credit score improved by 15 points.", "timestamp": "2024-08-23 09:00"},
    {"sender": "Customer", "recipient": "Client", "message": "That's great news, thank you!", "timestamp": "2024-08-23 09:15"},
    {"sender": "Client", "recipient": "Customer", "message": "A new credit account was opened in your name.", "timestamp": "2024-08-22 14:45"},
    {"sender": "Customer", "recipient": "Client", "message": "I did not authorize a new account. Please investigate.", "timestamp": "2024-08-22 15:10"},
    {"sender": "Client", "recipient": "Customer", "message": "We have initiated an investigation into the unauthorized account.", "timestamp": "2024-08-22 15:30"},
    {"sender": "Customer", "recipient": "Client", "message": "Thank you for your prompt action.", "timestamp": "2024-08-22 15:45"},
]

# Expanded sample data for credit updates
credit_updates_data = [
    {"update": "Credit score increased by 20 points.", "date": "2024-08-24"},
    {"update": "New inquiry on your credit report.", "date": "2024-08-23"},
    {"update": "Credit card balance paid off.", "date": "2024-08-22"},
    {"update": "Loan application approved.", "date": "2024-08-21"},
    {"update": "Dispute resolved in your favor.", "date": "2024-08-20"},
    {"update": "New credit account opened.", "date": "2024-08-19"},
    {"update": "Credit utilization reduced to 30%.", "date": "2024-08-18"},
    {"update": "Late payment recorded on credit report.", "date": "2024-08-17"},
    {"update": "Credit score decreased by 10 points.", "date": "2024-08-16"},
    {"update": "Debt-to-income ratio improved.", "date": "2024-08-15"},
]

# Convert to DataFrame
messages_df = pd.DataFrame(messages_data)
credit_updates_df = pd.DataFrame(credit_updates_data)

# Home Page
def home():
    st.title("Client-Customer Message & Board Updates")
    st.header("Recent Messages")
    st.dataframe(messages_df)
    
    st.header("Recent Credit Updates")
    st.dataframe(credit_updates_df)

# Messages Page
def messages():
    st.title("Messages")
    sender = st.selectbox("Sender", ["Client", "Customer"])
    recipient = "Customer" if sender == "Client" else "Client"
    message = st.text_area("Message")

    st.subheader("Message History")
    st.dataframe(messages_df)

    if st.button("Send Message"):
        new_message = {
            "sender": sender,
            "recipient": recipient,
            "message": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        messages_df.append(new_message, ignore_index=True)
        st.success("Message sent!")

        st.subheader("Updated Message History")
        st.dataframe(messages_df)
    
    st.subheader("Filter Messages")
    filter_sender = st.selectbox("Filter by Sender", ["All", "Client", "Customer"])
    if filter_sender != "All":
        filtered_df = messages_df[messages_df['sender'] == filter_sender]
    else:
        filtered_df = messages_df
    st.dataframe(filtered_df)
    
    st.subheader("Search Messages")
    search_term = st.text_input("Enter a keyword to search")
    if search_term:
        search_results = messages_df[messages_df['message'].str.contains(search_term, case=False)]
        st.dataframe(search_results)

# Credit Updates Page
def credit_updates():
    st.title("Credit Updates")
    st.subheader("Recent Credit Changes")
    st.dataframe(credit_updates_df)

    st.subheader("Add a New Credit Update")
    new_update = st.text_area("Describe the credit update")
    update_date = st.date_input("Date of Update", datetime.today())

    if st.button("Add Update"):
        new_credit_update = {
            "update": new_update,
            "date": update_date.strftime("%Y-%m-%d")
        }
        credit_updates_df.append(new_credit_update, ignore_index=True)
        st.success("Credit update added!")
        
        st.subheader("Updated Credit Updates")
        st.dataframe(credit_updates_df)

    st.subheader("Filter Credit Updates by Date")
    start_date = st.date_input("Start Date", datetime(2024, 1, 1))
    end_date = st.date_input("End Date", datetime.today())
    
    filtered_credit_updates = credit_updates_df[
        (credit_updates_df['date'] >= start_date.strftime("%Y-%m-%d")) & 
        (credit_updates_df['date'] <= end_date.strftime("%Y-%m-%d"))
    ]
    st.dataframe(filtered_credit_updates)

# Board Updates Page
def board_updates():
    st.title("Board Updates")
    st.subheader("Recent Announcements")
    st.write("No new board updates at the moment.")

    st.subheader("Post a New Board Update")
    board_update = st.text_area("Write your update")
    if st.button("Post Update"):
        st.success("Board update posted!")
        st.write("Here's what you posted:")
        st.write(board_update)
    
    st.subheader("Archived Board Updates")
    st.write("No archived updates available.")

# Navigation
menu = ["Home", "Messages", "Credit Updates", "Board Updates"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Home":
    home()
elif choice == "Messages":
    messages()
elif choice == "Credit Updates":
    credit_updates()
elif choice == "Board Updates":
    board_updates()
