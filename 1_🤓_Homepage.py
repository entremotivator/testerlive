import streamlit as st
from wordpress_auth import WordpressAuth

# ------------------------
# Page configuration
# ------------------------
st.set_page_config(
    page_title="VIP Credit Systems",
    page_icon="💳",
    layout="wide"
)

# ------------------------
# Session state initialization
# ------------------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'token' not in st.session_state:
    st.session_state.token = None

# ------------------------
# WordPress Auth
# ------------------------
def initialize_auth():
    try:
        base_url = st.secrets["general"]["base_url"]
        api_key = st.secrets["general"]["api_key"]
        return WordpressAuth(api_key=api_key, base_url=base_url)
    except KeyError as e:
        st.error(f"Missing secret configuration: {e}")
        st.stop()

def handle_login(username, password, auth):
    try:
        token = auth.get_token(username, password)
        if not token:
            st.sidebar.error("❌ Invalid credentials")
            return False

        if not auth.verify_token(token):
            st.sidebar.error("❌ Token verification failed")
            return False

        user_role = auth.get_user_role(token)
        if not user_role:
            st.sidebar.error("❌ Could not determine user role")
            return False

        user_role = user_role.lower()  # normalize
        if user_role == 'customer':
            st.sidebar.error("🚫 Access Denied - VIP required")
            st.sidebar.warning("[Join VIP Program](https://vipbusinesscredit.com/)")
            return False

        # Successful login
        st.session_state.authenticated = True
        st.session_state.user_role = user_role
        st.session_state.token = token
        st.sidebar.success(f"✅ Welcome, {user_role.title()}!")
        st.rerun()
        return True

    except Exception as e:
        st.sidebar.error(f"Login error: {str(e)}")
        return False

def logout():
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.token = None
    st.rerun()

# ------------------------
# Sidebar content
# ------------------------
def sidebar_content():
    with st.sidebar:
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.markdown("### 💳 VIP Credit")

        if not st.session_state.authenticated:
            st.markdown("### 🔐 Login")
            with st.form("sidebar_login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                login_button = st.form_submit_button("Login")

                if login_button and username and password:
                    auth = initialize_auth()
                    handle_login(username, password, auth)

            st.markdown("---")
            st.markdown("**New User?** [🌟 Join VIP Program](https://vipbusinesscredit.com/)")

        else:
            # Show user info and logout
            role_display = st.session_state.user_role.title() if st.session_state.user_role else "Unknown"
            st.success(f"👤 {role_display}")
            if st.button("🚪 Logout"):
                logout()
            st.markdown("---")
            st.info("📌 Select a page above to navigate")

# ------------------------
# Main home content
# ------------------------
def main_content():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.title("💳 VIP Credit Systems")
        st.title("VIP Credit Systems")
        st.subheader("Your Comprehensive Credit Management Solution")

        role = st.session_state.user_role.lower() if st.session_state.user_role else None

        if st.session_state.authenticated:
            # Role-based messages
            if role == 'administrator':
                st.info("🛠️ Administrator Access - Full system privileges")
            elif role == 'subscriber':
                st.info("📊 Subscriber Access - Credit dashboard enabled")
            else:
                st.info(f"✅ {role.title() if role else 'User'} Access - Welcome!")

            st.write("Welcome to **VIP Credit Systems**! Your dashboard is ready.")
        else:
            st.write("""
            Welcome to **VIP Credit Systems**. Please log in using the sidebar to access your dashboard.
            """)

# ------------------------
# Run the page
# ------------------------
sidebar_content()
main_content()

