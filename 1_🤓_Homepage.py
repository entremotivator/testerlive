import streamlit as st
from wordpress_auth import WordpressAuth

# Set page configuration
st.set_page_config(
    page_title="VIP Credit Systems",
    page_icon="💳",
    layout="wide"
)

# Initialize authentication state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'token' not in st.session_state:
    st.session_state.token = None

# Alternative approach: Define authorized usernames or use token-based validation
# You can replace this with actual usernames of subscribers and administrators
AUTHORIZED_USERS = {
    # Add actual usernames here - example:
    # 'admin_user': 'administrator',
    # 'subscriber1': 'subscriber',
    # 'subscriber2': 'subscriber'
}

def initialize_auth():
    """Initialize the WordPressAuth instance with secrets."""
    try:
        base_url = st.secrets["general"]["base_url"]
        api_key = st.secrets["general"]["api_key"]
        return WordpressAuth(api_key=api_key, base_url=base_url)
    except KeyError as e:
        st.error(f"Missing secret configuration: {e}")
        st.stop()

def get_user_info_safe(auth, token):
    """Safely get user information with available methods."""
    try:
        user_info = {}
        
        # Try to get username
        if hasattr(auth, 'get_username'):
            user_info['username'] = auth.get_username(token)
        elif hasattr(auth, 'get_user'):
            user_data = auth.get_user(token)
            if isinstance(user_data, dict):
                user_info.update(user_data)
            else:
                user_info['username'] = str(user_data)
        
        # Try to get user ID
        if hasattr(auth, 'get_user_id'):
            user_info['user_id'] = auth.get_user_id(token)
            
        # Try to get any user role if method exists
        if hasattr(auth, 'get_user_role'):
            user_info['role'] = auth.get_user_role(token)
        elif hasattr(auth, 'get_role'):
            user_info['role'] = auth.get_role(token)
            
        return user_info if user_info else None
        
    except Exception as e:
        st.sidebar.error(f"Error getting user info: {str(e)}")
        return None

def is_user_authorized(user_info):
    """Check if user is authorized based on available information."""
    if not user_info:
        return False, "No user information available"
    
    # Method 1: Check against authorized usernames list
    username = user_info.get('username', '').lower()
    if username in [u.lower() for u in AUTHORIZED_USERS.keys()]:
        return True, f"Authorized user: {username}"
    
    # Method 2: Check role if available
    role = user_info.get('role', '').lower()
    if role in ['subscriber', 'administrator']:
        return True, f"Authorized role: {role}"
    
    # Method 3: If no specific restrictions and user has valid token, allow access
    # (You can modify this logic based on your security requirements)
    if username and not role:
        # For now, we'll be restrictive and deny access if we can't determine role
        return False, f"Cannot verify authorization for user: {username}"
    
    return False, f"User not authorized - Username: {username}, Role: {role}"

def handle_login(username, password, auth):
    """Handle user login with flexible authorization checking."""
    try:
        # Get authentication token
        token = auth.get_token(username, password)
        
        if token and auth.verify_token(token):
            # Get user information
            user_info = get_user_info_safe(auth, token)
            
            # Check authorization
            is_authorized, auth_message = is_user_authorized(user_info)
            
            if not is_authorized:
                st.sidebar.error("🚫 **Access Denied**")
                st.sidebar.warning(f"""
                **Authorization Failed**
                
                {auth_message}
                
                **This system is restricted to:**
                - ✅ Subscriber accounts
                - ✅ Administrator accounts
                
                **To gain access:**
                [**Contact Support**](https://vipbusinesscredit.com/)
                """)
                return False
            
            # Allow access
            st.session_state.authenticated = True
            st.session_state.user_info = user_info
            st.session_state.token = token
            
            display_name = user_info.get('username', 'User')
            role = user_info.get('role', 'Authorized User')
            st.sidebar.success(f"✅ Welcome, {display_name}!")
            st.sidebar.info(f"Status: {role.title()}")
            st.rerun()
            return True
            
        else:
            st.sidebar.error("❌ Invalid credentials")
            return False
            
    except Exception as e:
        st.sidebar.error(f"Login error: {str(e)}")
        return False

def logout():
    """Handle user logout."""
    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.session_state.token = None
    st.rerun()

def sidebar_content():
    """Handle sidebar content - login form or user info."""
    with st.sidebar:
        # Logo
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.markdown("### 💳 VIP Credit")
        
        if not st.session_state.authenticated:
            # Login Form
            st.markdown("### 🔐 Login")
            
            with st.form("sidebar_login_form"):
                username = st.text_input("Username", placeholder="Enter username")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                login_button = st.form_submit_button("Login", use_container_width=True)
                
                if login_button and username and password:
                    auth = initialize_auth()
                    handle_login(username, password, auth)
            
            # Access information
            st.markdown("---")
            st.markdown("**Access Requirements**")
            st.info("""
            **Authorized Access:**
            - ✅ Subscriber accounts
            - ✅ Administrator accounts
            - ✅ Authorized users
            
            **Restricted:**
            - ❌ Customer accounts
            - ❌ Unauthorized users
            """)
            
            st.markdown("[🌟 Get Access](https://vipbusinesscredit.com/)")
                
        else:
            # User info and logout
            user_info = st.session_state.user_info or {}
            display_name = user_info.get('username', 'User')
            role = user_info.get('role', 'Authorized')
            
            st.success(f"👤 {display_name}")
            st.caption(f"🔑 {role.title()}")
            
            if st.button("🚪 Logout", use_container_width=True):
                logout()
            
            st.markdown("---")
            st.info("📌 Select a page above to navigate")

def main_content():
    """Display the main home page content."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Main logo
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.title("💳 VIP Credit Systems")

        st.title("VIP Credit Systems")
        st.subheader("Your Comprehensive Credit Management Solution")

        if st.session_state.authenticated:
            # Welcome message for authenticated users
            user_info = st.session_state.user_info or {}
            display_name = user_info.get('username', 'User')
            role = user_info.get('role', 'authorized user')
            
            if role.lower() == 'administrator':
                st.info("🛠️ **Administrator Access** - Full system privileges")
            elif role.lower() == 'subscriber':
                st.info("📊 **Subscriber Access** - Credit dashboard enabled")
            else:
                st.info(f"✅ **Authorized Access** - Welcome {display_name}!")

            # Introduction for authenticated users
            st.write(f"""
            Welcome to **VIP Credit Systems**, {display_name}! Your comprehensive credit management dashboard is ready. 
            Use the navigation menu above to access all features and start optimizing your credit profile.
            """)

            # Feature categories
            st.markdown("## 🎯 Available Features")
            
            # Credit Overview Section
            with st.expander("📊 Credit Overview", expanded=True):
                st.markdown("""
                - **Credit Score Overview** - Real-time credit score monitoring
                - **Credit Utilization** - Track your credit usage across all accounts
                - **Payment History** - Comprehensive payment tracking
                - **Credit Report Summary** - Detailed credit report analysis
                """)

            # Account Management Section
            with st.expander("🔧 Account Management"):
                st.markdown("""
                - **Credit Inquiries** - Monitor hard and soft credit pulls
                - **Credit Limits** - Track and optimize credit limits
                - **Debt-to-Income Ratio** - Calculate and monitor DTI
                - **Account Balances** - Overview of all loan and credit card balances
                """)

            # Analytics Section
            with st.expander("📈 Analytics & Insights"):
                st.markdown("""
                - **Account Age Analysis** - Track credit history length
                - **Monthly Payment Tracking** - Monitor payment patterns
                - **Credit Account Breakdown** - Detailed account analysis
                - **Top Account Balances** - Focus on highest impact accounts
                """)

            # Tools Section
            with st.expander("🛠️ Credit Management Tools"):
                st.markdown("""
                - **Credit Score Simulation** - Preview impact of financial decisions
                - **Debt Reduction Planning** - Strategic payoff planning
                - **Credit Building Tips** - Personalized improvement recommendations
                - **Alert System** - Stay informed of important changes
                """)

            # Call to action
            st.markdown("---")
            st.success("""
            🚀 **Ready to get started?** 
            
            Use the navigation menu above to explore your credit management tools and start optimizing your financial profile today!
            """)
            
        else:
            # Content for non-authenticated users
            st.write("""
            Welcome to **VIP Credit Systems**, where managing your credit has never been easier. 
            Our system provides comprehensive tools and insights to help you understand and optimize your credit profile.
            
            **Please log in using the sidebar to access your credit management dashboard.**
            """)

            # Access requirements
            st.markdown("---")
            st.warning("""
            🔐 **Access Requirements** 
            
            This system is restricted to authorized accounts only.
            
            [**Contact Support for Access**](https://vipbusinesscredit.com/)
            """)

# Main application logic
sidebar_content()
main_content()

