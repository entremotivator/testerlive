import streamlit as st
from wordpress_auth import WordpressAuth

# ------------------------
# Configuration Sidebar
# ------------------------
def get_user_input():
    with st.sidebar:
        st.title("Configuration Settings")
        wordpress_url = st.text_input("WordPress Site URL", placeholder="https://yourwordpressurl.com")
        api_key_input = st.text_input("API Key", type='password')
        return wordpress_url, api_key_input

# ------------------------
# Main Page
# ------------------------
def main_page(user_role):
    st.title(f"Welcome, {user_role.capitalize()}!")
    if user_role == 'administrator':
        st.write("You have full access to admin features.")
    elif user_role == 'subscriber':
        st.write("You have access to subscriber-only content.")
    # Optionally, add more role-specific content here

# ------------------------
# Login Page
# ------------------------
def login_page(auth):
    st.title("WordPress Login")
    with st.form(key='login_form'):
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type='password')
        submit_button = st.form_submit_button("Log In")

        if submit_button:
            token = auth.get_token(username_input, password_input)
            if token and auth.verify_token(token):
                user_role = auth.get_user_role(token)  # Assumes WordpressAuth has this method
                if user_role in ['subscriber', 'administrator']:
                    st.session_state['token'] = token
                    st.session_state['role'] = user_role
                    st.success(f"Logged in successfully as {user_role}!")
                    st.experimental_rerun()
                elif user_role == 'customer':
                    st.error("Access denied. Customers are not allowed.")
                else:
                    st.error(f"Access denied. Your role '{user_role}' is not allowed.")
            else:
                st.error("Invalid credentials. Please try again.")

# ------------------------
# Logout Button
# ------------------------
def logout():
    if 'token' in st.session_state:
        if st.sidebar.button("Log Out"):
            del st.session_state['token']
            del st.session_state['role']
            st.success("Logged out successfully.")
            st.experimental_rerun()

# ------------------------
# App Logic
# ------------------------
wordpress_url, api_key_input = get_user_input()

if wordpress_url and api_key_input:
    auth = WordpressAuth(api_key=api_key_input, base_url=wordpress_url)
    
    if 'token' in st.session_state and auth.verify_token(st.session_state['token']):
        main_page(st.session_state['role'])
    else:
        login_page(auth)

    logout()
else:
    st.warning("Please enter the WordPress site URL and API key in the sidebar.")
