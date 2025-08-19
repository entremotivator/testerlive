import streamlit as st
from wordpress_auth import WordpressAuth

# ------------------------
# Page configuration
# ------------------------
st.set_page_config(
    page_title="VIP Credit Systems - Login",
    page_icon="🔐",
    layout="wide"
)

# ------------------------
# Initialize session state
# ------------------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'token' not in st.session_state:
    st.session_state.token = None

# Define allowed roles - ONLY subscriber and administrator
ALLOWED_ROLES = ['subscriber', 'administrator']

# ------------------------
# Initialize WordPress authentication
# ------------------------
def initialize_auth():
    """Initialize the WordPressAuth instance with secrets."""
    try:
        base_url = st.secrets["general"]["base_url"]
        api_key = st.secrets["general"]["api_key"]
        return WordpressAuth(api_key=api_key, base_url=base_url)
    except KeyError as e:
        st.error(f"Missing secret configuration: {e}")
        st.stop()

def is_role_allowed(user_role):
    """Check if user role is in the allowed list."""
    if not user_role:
        return False
    return user_role.lower() in ALLOWED_ROLES

# ------------------------
# Handle login with strict role checking
# ------------------------
def handle_login(username, password, auth):
    """Authenticate user and verify role - ONLY allow subscriber and administrator."""
    try:
        token = auth.get_token(username, password)
        if not token:
            st.error("❌ **Invalid username or password.** Please try again.")
            return False

        if not auth.verify_token(token):
            st.error("❌ **Token verification failed.**")
            return False

        user_role = auth.get_user_role(token)
        if not user_role:
            st.error("❌ Could not determine your user role.")
            return False

        user_role = user_role.lower()

        # Strict role checking - ONLY allow subscriber and administrator
        if not is_role_allowed(user_role):
            st.error("🚫 **Access Denied - Insufficient Privileges**")
            st.warning(f"""
            ### Your account role: **{user_role.title()}**
            
            **This system is restricted to:**
            - ✅ **Subscriber** accounts
            - ✅ **Administrator** accounts
            
            **Your role "{user_role}" is not authorized for access.**
            
            **To gain access:**
            - 📞 [**Contact Support**](https://vipbusinesscredit.com/)
            - 🔄 Request role upgrade from your administrator
            """)
            return False

        # Allow access for subscriber and administrator only
        st.session_state.authenticated = True
        st.session_state.user_role = user_role
        st.session_state.token = token
        st.success(f"✅ **Welcome!** Logged in as {user_role.title()}")
        st.balloons()
        st.info("🔄 Redirecting to your dashboard...")
        st.rerun()
        return True

    except Exception as e:
        st.error(f"🚨 Login error: {str(e)}")
        return False

# ------------------------
# Login page UI
# ------------------------
def login_page():
    """Display login interface with strict access control."""
    if st.session_state.authenticated:
        st.success(f"✅ Already logged in as {st.session_state.user_role.title()}")
        st.info("🏠 [Go to Home Page](Home)")
        return

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Logo
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.title("💳 VIP Credit Systems")

        st.markdown("### 🔐 Secure Login")
        st.markdown("Access restricted to authorized personnel only")

        # Access requirements notice
        st.info("""
        🔒 **Access Requirements:**
        - ✅ **Subscriber** accounts
        - ✅ **Administrator** accounts
        - ❌ **Customer** accounts (not authorized)
        - ❌ **Other roles** (not authorized)
        """)

        # Login form
        with st.form("login_form", clear_on_submit=False):
            st.markdown("#### Enter Your Credentials")
            username = st.text_input("Username", placeholder="Enter your username", help="Use your WordPress username")
            password = st.text_input("Password", type="password", placeholder="Enter your password", help="Use your WordPress password")

            col_login, col_clear = st.columns([3, 1])
            with col_login:
                login_button = st.form_submit_button("🔐 Login", use_container_width=True, type="primary")
            with col_clear:
                clear_button = st.form_submit_button("🗑️ Clear")

            if login_button and username and password:
                with st.spinner("🔄 Authenticating and verifying permissions..."):
                    auth = initialize_auth()
                    handle_login(username, password, auth)

            if clear_button:
                st.rerun()

        st.markdown("---")
        st.markdown("### 🔐 Access Control Information")

        col_access, col_contact = st.columns([1, 1])
        with col_access:
            st.markdown("""
            **Authorized Roles:**
            - 🛠️ **Administrator** - Full system access
            - 📊 **Subscriber** - Dashboard access
            """)
        with col_contact:
            st.markdown("""
            **Need Access?**
            - 📞 [**Contact Support**](https://vipbusinesscredit.com/)
            - 🔄 Request role upgrade
            """)

        st.markdown("---")
        with st.expander("❓ Access & Security Information"):
            st.markdown("""
            **Security Notice:**
            This system implements strict role-based access control. Only users with **Subscriber** or **Administrator** roles are permitted to access the VIP Credit Systems dashboard.

            **If you're having access issues:**
            1. Verify your WordPress account is active
            2. Confirm your role assignment with your administrator
            3. Contact support if you believe you should have access

            **Role Definitions:**
            - **Administrator**: Full system privileges and management capabilities
            - **Subscriber**: Access to credit monitoring and dashboard features
            - **Customer**: Standard website access only (no dashboard access)
            - **Other roles**: Contact administrator for access evaluation
            """)

# ------------------------
# Run the page
# ------------------------
login_page()

