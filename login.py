import streamlit as st
from wordpress_auth import WordpressAuth

# Set page configuration
st.set_page_config(
    page_title="VIP Credit Systems - Login",
    page_icon="🔐",
    layout="wide"
)

# Initialize authentication state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'token' not in st.session_state:
    st.session_state.token = None

def initialize_auth():
    """Initialize the WordPressAuth instance with secrets."""
    try:
        base_url = st.secrets["general"]["base_url"]
        api_key = st.secrets["general"]["api_key"]
        return WordpressAuth(api_key=api_key, base_url=base_url)
    except KeyError as e:
        st.error(f"Missing secret configuration: {e}")
        st.stop()

def handle_login(username, password, auth):
    """Handle user login and role verification."""
    try:
        # Get authentication token
        token = auth.get_token(username, password)
        
        if token and auth.verify_token(token):
            user_role = auth.get_user_role(token)
            
            # Check if user role is 'customer' - deny access
            if user_role == 'customer':
                st.error("🚫 **Access Denied**")
                st.warning("""
                ### Your account needs to be upgraded to access VIP Credit Systems.
                
                **Options to get access:**
                - 🌟 [**Join our VIP Program**](https://vipbusinesscredit.com/)
                - 💳 [**Update your payment information**](https://vipbusinesscredit.com/)
                
                **What you'll get with VIP access:**
                - Complete credit monitoring and reporting
                - Advanced credit building tools
                - Expert guidance and personalized support
                - Business credit optimization strategies
                """)
                return False
            
            # Allow access for all other roles
            st.session_state.authenticated = True
            st.session_state.user_role = user_role
            st.session_state.token = token
            st.success(f"✅ **Welcome!** Logged in as {user_role.title()}")
            st.balloons()
            
            # Auto redirect to home page after short delay
            st.info("🔄 Redirecting to your dashboard...")
            st.rerun()
            return True
            
        else:
            st.error("❌ **Invalid username or password.** Please try again.")
            return False
            
    except Exception as e:
        st.error(f"🚨 Login error: {str(e)}")
        return False

def login_page():
    """Display login interface."""
    # Check if already authenticated
    if st.session_state.authenticated:
        st.success(f"✅ Already logged in as {st.session_state.user_role.title()}")
        st.info("🏠 [Go to Home Page](Home)")
        return
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Logo and title
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.title("💳 VIP Credit Systems")
        
        st.markdown("### 🔐 Login to Your Account")
        st.markdown("Access your comprehensive credit management dashboard")
        
        # Login form
        with st.form("login_form", clear_on_submit=False):
            st.markdown("#### Enter Your Credentials")
            username = st.text_input(
                "Username", 
                placeholder="Enter your username",
                help="Use your WordPress username"
            )
            password = st.text_input(
                "Password", 
                type="password", 
                placeholder="Enter your password",
                help="Use your WordPress password"
            )
            
            col_login, col_clear = st.columns([3, 1])
            with col_login:
                login_button = st.form_submit_button(
                    "🔐 Login", 
                    use_container_width=True,
                    type="primary"
                )
            with col_clear:
                clear_button = st.form_submit_button("🗑️ Clear")
            
            if login_button and username and password:
                with st.spinner("🔄 Authenticating..."):
                    auth = initialize_auth()
                    handle_login(username, password, auth)
            
            if clear_button:
                st.rerun()
        
        # Divider
        st.markdown("---")
        
        # Sign up section
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
        
        # Help section
        st.markdown("---")
        with st.expander("❓ Need Help?"):
            st.markdown("""
            **Having trouble logging in?**
            
            - Make sure you're using your WordPress credentials
            - Check that your account is active and has the proper permissions
            - Contact support if you continue having issues
            
            **Account Access Levels:**
            - ✅ **Administrator** - Full system access
            - ✅ **Subscriber** - Credit dashboard access  
            - ✅ **Editor/Author** - Standard access
            - ❌ **Customer** - Requires VIP upgrade
            """)

# Main application
login_page()
