import streamlit as st
import requests
from supabase import create_client, Client

# ----------------------
# Supabase Setup
# ----------------------
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----------------------
# RentCast Setup
# ----------------------
RENTCAST_API_KEY = st.secrets["rentcast"]["api_key"]
RENTCAST_BASE_URL = "https://api.rentcast.io/v1"
MAX_QUERIES = 30

# ----------------------
# Authentication
# ----------------------
def login(email, password):
    """Login existing user"""
    try:
        user = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return user
    except Exception as e:
        st.error(f"Login failed: {e}")
        return None

def signup(email, password):
    """Register a new user and initialize usage record"""
    try:
        user = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        # Initialize API usage tracking
        if user and user.user:
            supabase.table("api_usage").insert({
                "user_id": user.user.id,
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
    """Fetch current query usage, initialize if missing"""
    response = supabase.table("api_usage").select("*").eq("user_id", user_id).execute()
    if response.data:
        return response.data[0]["queries"]
    else:
        supabase.table("api_usage").insert({
            "user_id": user_id,
            "email": email,
            "queries": 0
        }).execute()
        return 0

def increment_usage(user_id):
    """Increment query count for user"""
    usage = get_user_usage(user_id, "")
    supabase.table("api_usage").update({
        "queries": usage + 1
    }).eq("user_id", user_id).execute()

# ----------------------
# RentCast Request
# ----------------------
def fetch_property_details(address, user_id, email):
    """Call RentCast API for property details"""
    usage = get_user_usage(user_id, email)
    if usage >= MAX_QUERIES:
        st.error("🚫 You have reached your 30 API query limit.")
        return None

    headers = {
        "accept": "application/json",
        "X-Api-Key": RENTCAST_API_KEY
    }
    params = {"address": address}
    response = requests.get(f"{RENTCAST_BASE_URL}/properties", headers=headers, params=params)

    if response.status_code == 200:
        increment_usage(user_id)
        return response.json()
    else:
        st.error("⚠️ Error fetching data from RentCast API.")
        return None

# ----------------------
# Streamlit App UI
# ----------------------
st.set_page_config(page_title="🏡 RentCast API App", page_icon="🏠")
st.title("🏡 RentCast API with Supabase Auth")

# Session State init
if "user" not in st.session_state:
    st.session_state.user = None

# Not logged in → show login/signup tabs
if st.session_state.user is None:
    tab1, tab2 = st.tabs(["🔑 Login", "🆕 Sign Up"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login"):
            user = login(email, password)
            if user:
                st.session_state.user = user
                st.success("✅ Logged in successfully!")

    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pw")
        if st.button("Sign Up"):
            user = signup(email, password)
            if user:
                st.success("🎉 Account created! Please log in.")

# Logged in → main app
else:
    user_id = st.session_state.user.user.id
    email = st.session_state.user.user.email

    st.success(f"👋 Welcome {email}!")

    st.subheader("🏠 Search Property on RentCast")
    address = st.text_input("Enter Property Address")

    if st.button("Fetch Property"):
        data = fetch_property_details(address, user_id, email)
        if data:
            st.json(data)
            queries_used = get_user_usage(user_id, email)
            st.info(f"🔢 API Queries Used: {queries_used}/{MAX_QUERIES}")

    if st.button("Logout"):
        st.session_state.user = None
        st.success("👋 Logged out successfully!")
