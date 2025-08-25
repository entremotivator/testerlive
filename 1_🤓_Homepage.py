import streamlit as st
import requests
from supabase import create_client, Client

# ----------------------
# Supabase Setup
# ----------------------
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_ANON_KEY = st.secrets["supabase"]["anon_key"]  # for auth operations
SUPABASE_SERVICE_KEY = st.secrets["supabase"]["service_key"]  # optional, for admin tasks

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)  # user client by default

# ----------------------
# RentCast Setup
# ----------------------
RENTCAST_API_KEY = st.secrets["rentcast"]["api_key"]
RENTCAST_BASE_URL = "https://api.rentcast.io/v1"
MAX_QUERIES = 30

# ----------------------
# Helpers
# ----------------------
def get_user_client():
    """Return a Supabase client authorized with the current user’s access token."""
    if "access_token" not in st.session_state:
        return None
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.postgrest.auth(st.session_state.access_token)
    return client

# ----------------------
# Authentication
# ----------------------
def login(email, password):
    try:
        user = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if user and user.session:
            st.session_state.access_token = user.session.access_token
            st.session_state.user = user.user
        return user
    except Exception as e:
        st.error(f"Login failed: {e}")
        return None

def signup(email, password):
    try:
        user = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        if user and user.session:
            st.session_state.access_token = user.session.access_token
            st.session_state.user = user.user

            # Insert usage row under user context
            client = get_user_client()
            if client:
                client.table("api_usage").insert({
                    "user_id": str(user.user.id),
                    "email": email,
                    "queries": 0
                }).execute()
        return user
    except Exception as e:
        st.error(f"Signup failed: {e}")
        return None

# ----------------------
# Query Tracker
# ----------------------
def get_user_usage(user_id, email):
    client = get_user_client()
    if not client:
        return 0

    response = client.table("api_usage").select("*").eq("user_id", user_id).execute()
    if response.data:
        return response.data[0]["queries"]
    else:
        # create row if missing
        client.table("api_usage").insert({
            "user_id": str(user_id),
            "email": email,
            "queries": 0
        }).execute()
        return 0

def increment_usage(user_id, email):
    current = get_user_usage(user_id, email)
    client = get_user_client()
    if client:
        client.table("api_usage").update({
            "queries": current + 1
        }).eq("user_id", user_id).execute()

# ----------------------
# RentCast Request
# ----------------------
def fetch_property_details(address, user_id, email):
    usage = get_user_usage(user_id, email)
    if usage >= MAX_QUERIES:
        st.error("You have reached your 30 API query limit.")
        return None
    
    headers = {"accept": "application/json", "X-Api-Key": RENTCAST_API_KEY}
    params = {"address": address}
    response = requests.get(f"{RENTCAST_BASE_URL}/properties", headers=headers, params=params)

    if response.status_code == 200:
        increment_usage(user_id, email)
        return response.json()
    else:
        st.error("Error fetching data from RentCast API.")
        return None

# ----------------------
# Streamlit App UI
# ----------------------
st.title("🏡 RentCast API with Supabase Auth")

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        email = st.text_input("Email (Login)", key="login_email")
        password = st.text_input("Password (Login)", type="password", key="login_pw")
        if st.button("Login"):
            user = login(email, password)
            if user:
                st.success("Logged in successfully!")

    with tab2:
        email = st.text_input("Email (Signup)", key="signup_email")
        password = st.text_input("Password (Signup)", type="password", key="signup_pw")
        if st.button("Sign Up"):
            user = signup(email, password)
            if user:
                st.success("Account created and logged in!")

else:
    user_id = st.session_state.user.id
    email = st.session_state.user.email
    st.success(f"Welcome {email}!")

    st.subheader("Search Property on RentCast")
    address = st.text_input("Enter Property Address")

    if st.button("Fetch Property"):
        data = fetch_property_details(address, user_id, email)
        if data:
            st.json(data)

    queries_used = get_user_usage(user_id, email)
    st.info(f"API Queries Used: {queries_used}/{MAX_QUERIES}")

    if st.button("Logout"):
        st.session_state.user = None
        st.session_state.access_token = None
        st.success("Logged out successfully!")
