import streamlit as st
import requests

# ------------------------------
# WordPress Authentication Class
# ------------------------------
class WordpressAuth:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def get_token(self, username, password):
        """
        Authenticate user and fetch JWT token + roles.
        Returns (token, user_data) or (None, None).
        """
        try:
            # 1. Get JWT token
            token_url = f"{self.base_url}/wp-json/jwt-auth/v1/token"
            response = requests.post(token_url, data={
                "username": username,
                "password": password
            })

            if response.status_code != 200:
                return None, None

            data = response.json()
            token = data.get("token")

            if not token:
                return None, None

            # 2. Get user info (to check roles)
            user_url = f"{self.base_url}/wp-json/wp/v2/users/me"
            user_res = requests.get(user_url, headers={
                "Authorization": f"Bearer {token}"
            })

            if user_res.status_code != 200:
                return token, {"roles": []}

            user_data = user_res.json()
            return token, user_data

        except Exception as e:
            st.error(f"Auth error: {e}")
            return None, None


# ------------------------------
# Initialize Authentication
# ------------------------------
if "auth" not in st.session_state:
    st.session_state.auth = None

def initialize_auth():
    """Initialize the WordPressAuth instance with secrets."""
    try:
        base_url = st.secrets["general"]["base_url"]
        api_key = st.secrets["general"]["api_key"]
        return WordpressAuth(api_key=api_key, base_url=base_url)
    except KeyError as e:
        st.error(f"Missing secret: {e}")
        st.stop()

def login(username, password):
    """Handle user login process."""
    auth = st.session_state.auth
    if auth:
        token, user_data = auth.get_token(username, password)
        if token:
            # Check user role(s)
            user_roles = user_data.get("roles", [])

            # ✅ Only allow admin + subscriber
            if not any(role in ["administrator", "subscriber"] for role in user_roles):
                st.error("🚫 Access denied. Only Administrators and Subscribers are allowed.")
                st.session_state.authenticated = False
                return

            # Allow login for admin + subscriber
            st.session_state.authenticated = True
            st.session_state.token = token
            st.session_state.user_roles = user_roles
            st.success(f"✅ Login successful! Roles: {', '.join(user_roles)}")
        else:
            st.error("❌ Invalid username or password")
    else:
        st.error("Authentication system is not initialized.")


# ------------------------------
# Streamlit App Config
# ------------------------------
st.set_page_config(
    page_title="VIP Credit Systems",
    page_icon="💳",
    layout="wide"
)

# Initialize authentication
if st.session_state.auth is None:
    st.session_state.auth = initialize_auth()

# Initialize authentication state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


# ------------------------------
# Login Sidebar
# ------------------------------
if not st.session_state.authenticated:
    with st.sidebar:
        st.header("Login")
        with st.form(key='login_form'):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")

        if login_button:
            login(username, password)

        st.sidebar.markdown("---")
        st.sidebar.markdown("[Sign Up](https://vipbusinesscredit.com/)")


# ------------------------------
# Main Content (Only if logged in)
# ------------------------------
if st.session_state.authenticated:
    with st.sidebar:
        st.image("logooo.png", use_column_width=True)
        st.success("Select a page above.")

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.image("logooo.png", use_column_width=True)

        st.title("VIP Credit Systems")
        st.subheader("Your Comprehensive Credit Management Solution")

        st.write("""
        Welcome to **VIP Credit Systems**, where managing your credit has never been easier. 
        Our system provides a wide range of tools and insights to help you understand and optimize 
        your credit profile. Below is a detailed list of features we offer.
        """)

        st.markdown("""
        ## Features:
        
        ### Credit Overview
        - 📊 **Credit Score Overview**
        - 💳 **Credit Utilization**
        - 🗓️ **Payment History**
        - 📑 **Credit Report Summary**

        ### Account Management
        - 🔍 **Credit Inquiries**
        - 🎯 **Credit Limits**
        - ⚖️ **Debt-to-Income Ratio**
        - 💰 **Loan and Credit Card Balances**

        ### Analytics and Insights
        - ⏳ **Account Age**
        - 💵 **Monthly Payments**
        - 📂 **Credit Accounts Breakdown**
        - 🏆 **Top 5 Highest Balances**

        ### Transactions and Payments
        - 📝 **Top 5 Recent Transactions**
        - 📅 **Upcoming Payments**
        - 🔄 **Credit Utilization by Account Type**
        - 📈 **Average Payment History**

        ### Trends and Forecasting
        - 📊 **Credit Score Trend**
        - 💸 **Monthly Spending Trend**
        - 📉 **Credit Score vs. Credit Utilization**
        - 📅 **Debt Repayment Schedule**

        ### Credit Management Tools
        - 🆕 **New Credit Accounts**
        - 🧠 **Credit Score Impact Simulation**
        - 📉 **Debt Reduction Plan**
        - 💡 **Credit Score Improvement Tips**

        ### Customization and Alerts
        - ⚠️ **Alerts and Recommendations**
        - ✏️ **Edit Credit Info**
        - 📤 **Export Data**
        """)

        st.write("""
        Explore these features and more in the VIP Credit Systems app. 
        Whether you are looking to improve your credit score, manage your debts, 
        or simply stay on top of your financial health, we've got you covered.
        """)
else:
    st.write("🔐 Please log in to access the VIP Credit Systems.")
