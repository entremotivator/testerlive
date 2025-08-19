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
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'token' not in st.session_state:
    st.session_state.token = None

# Alternative approach: Define authorized usernames or use flexible validation
# You can replace this with actual usernames of subscribers and administrators
AUTHORIZED_USERS = {
    # Add actual usernames here - example:
    # 'admin_user': 'administrator',
    # 'subscriber1': 'subscriber',
    # 'subscriber2': 'subscriber'
}

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
        st.error(f"Error getting user info: {str(e)}")
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
    
    # Method 3: Block known restricted roles
    if role == 'customer':
        return False, f"Customer role is not authorized for system access"
    
    # Method 4: If no specific restrictions and user has valid token, you can choose to:
    # Option A: Allow access (less secure)
    # Option B: Deny access (more secure) - current implementation
    if username and not role:
        return False, f"Cannot verify authorization for user: {username} (role unknown)"
    
    return False, f"User not authorized - Username: {username}, Role: {role}"

# ------------------------
# Handle login with flexible authorization
# ------------------------
def handle_login(username, password, auth):
    """Authenticate user with flexible authorization checking."""
    try:
        token = auth.get_token(username, password)
        if not token:
            st.error("❌ **Invalid username or password.** Please try again.")
            return False

        if not auth.verify_token(token):
            st.error("❌ **Token verification failed.**")
            return False

        # Get user information
        user_info = get_user_info_safe(auth, token)
        
        # Check authorization
        is_authorized, auth_message = is_user_authorized(user_info)
        
        if not is_authorized:
            st.error("🚫 **Access Denied**")
            st.warning(f"""
            ### Authorization Failed
            
            **Details:** {auth_message}
            
            **This system is restricted to:**
            - ✅ **Subscriber** accounts
            - ✅ **Administrator** accounts
            - ✅ **Authorized users**
            
            **Not allowed:**
            - ❌ **Customer** accounts
            - ❌ **Unauthorized roles**
            
            **To gain access:**
            - 📞 [**Contact Support**](https://vipbusinesscredit.com/)
            - 🔄 Request role upgrade from your administrator
            """)
            return False

        # Allow access
        st.session_state.authenticated = True
        st.session_state.user_info = user_info
        st.session_state.token = token
        
        display_name = user_info.get('username', 'User')
        role = user_info.get('role', 'Authorized User')
        
        st.success(f"✅ **Welcome!** Logged in as {display_name}")
        st.info(f"Access Level: {role.title()}")
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
    """Display login interface with flexible access control."""
    if st.session_state.authenticated:
        user_info = st.session_state.user_info or {}
        display_name = user_info.get('username', 'User')
        st.success(f"✅ Already logged in as {display_name}")
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
        st.markdown("Access control with flexible authorization")

        # Access requirements notice
        st.info("""
        🔒 **Access Requirements:**
        - ✅ **Subscriber** accounts
        - ✅ **Administrator** accounts  
        - ✅ **Authorized users**
        - ❌ **Customer** accounts (restricted)
        - ❌ **Unauthorized roles**
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
                with st.spinner("🔄 Authenticating and checking authorization..."):
                    auth = initialize_auth()
                    handle_login(username, password, auth)

            if clear_button:
                st.rerun()

        st.markdown("---")
        st.markdown("### 🔐 Authorization Information")

        col_access, col_contact = st.columns([1, 1])
        with col_access:
            st.markdown("""
            **Authorized Access:**
            - 🛠️ **Administrator** - Full system access
            - 📊 **Subscriber** - Dashboard access
            - ✅ **Authorized users** - Verified access
            """)
        with col_contact:
            st.markdown("""
            **Need Access?**
            - 📞 [**Contact Support**](https://vipbusinesscredit.com/)
            - 🔄 Request authorization
            - 📧 Verify account status
            """)

        st.markdown("---")
        with st.expander("❓ Access Control & Troubleshooting"):
            st.markdown("""
            **Access Control System:**
            This system uses flexible authorization that checks multiple factors:
            1. **Role-based access** - Subscriber and Administrator roles are automatically authorized
            2. **User-based access** - Specific authorized users can be granted access
            3. **Restriction enforcement** - Customer roles and unauthorized users are blocked
            
            **Authorization Process:**
            1. Username and password verification
            2. Token validation
            3. User information retrieval
            4. Authorization level checking
            5. Access granted or denied based on criteria
            
            **If you're having access issues:**
            - Verify your WordPress credentials are correct
            - Check that your account role is properly assigned
            - Ensure your account is active and not suspended
            - Contact support if you believe you should have access
            
            **Troubleshooting Authentication Errors:**
            - "Role method not found" - Contact support for system configuration
            - "Cannot verify authorization" - Your role may need to be updated
            - "User not authorized" - Request access upgrade from administrator
            """)

# ------------------------
# Run the page
# ------------------------
login_page()

