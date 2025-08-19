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

# ------------------------
# Handle login
# ------------------------
def handle_login(username, password, auth):
    """Authenticate user and verify role."""
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

        # ONLY allow subscriber and administrator roles
        if user_role not in ['subscriber', 'administrator']:
            st.error("🚫 **Access Denied**")
            st.warning(f"""
            ### Your account role: **{user_role.title()}**
            
            **This system is restricted to:**
            - ✅ **Subscriber** accounts
            - ✅ **Administrator** accounts
            
            **Your role "{user_role}" is not authorized.**
            
            **To gain access:**
            - 📞 [**Contact Support**](https://vipbusinesscredit.com/)
            - 🔄 Request role upgrade from administrator
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
    """Display login interface."""
    if st.session_state.authenticated:
        st.success(f"✅ Already logged in as {st.session_state.user_role.title()}")
        st.info("🏠 [Go to Home Page](Home)")
        return

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Logo
        try:
            st.image("logooo.png", use_container_width=True)
        except:
            st.title("💳 VIP Credit Systems")

        st.markdown("### 🔐 Login to Your Account")
        st.markdown("Access your comprehensive credit management dashboard")

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
                with st.spinner("🔄 Authenticating..."):
                    auth = initialize_auth()
                    handle_login(username, password, auth)

            if clear_button:
                st.rerun()

        st.markdown("---")
        st.markdown("### 🌟 New to VIP Credit Systems?")

        col_join, col_info = st.columns([1, 1])
        with col_join:
            st.markdown("""
            **Ready to take control of your credit?**
            [**🚀 Join VIP Business Credit →**](https://vipbusinesscredit.com/)
            """)
        with col_info:
            st.markdown("""
            **What's included:**
            - ✅ Complete credit monitoring
            - ✅ Business credit building tools  
            - ✅ Expert guidance & support
            - ✅ Personalized strategies
            """)

        st.markdown("---")
        with st.expander("❓ Need Help?"):
            st.markdown("""
            **Having trouble logging in?**
            - Use your WordPress credentials
            - Ensure your account is active with proper permissions
            - Contact support if issues persist

            **Account Access Levels:**
            - ✅ **Administrator** - Full system access
            - ✅ **Subscriber** - Credit dashboard access
            - ❌ **Customer** - Not authorized
            - ❌ **Editor/Author** - Not authorized
            - ❌ **Other roles** - Not authorized
            """)

# ------------------------
# Run the page
# ------------------------
login_page()
