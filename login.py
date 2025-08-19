import streamlit as st
from wordpress_auth import WordpressAuth

# ------------------------
# Page configuration
# ------------------------
st.set_page_config(
    page_title="VIP Credit Systems - Secure Login",
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
if 'login_attempts' not in st.session_state:
    st.session_state.login_attempts = 0

# Security configuration - ONLY these roles are permitted
AUTHORIZED_ROLES = {
    'subscriber': {
        'name': 'Subscriber',
        'access_level': 'standard',
        'description': 'Credit monitoring and dashboard access',
        'permissions': ['view_dashboard', 'view_reports']
    },
    'administrator': {
        'name': 'Administrator',
        'access_level': 'full', 
        'description': 'Complete system administration access',
        'permissions': ['view_dashboard', 'view_reports', 'manage_users', 'system_config']
    }
}

# Maximum login attempts before temporary lockout
MAX_LOGIN_ATTEMPTS = 5

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

def validate_user_authorization(user_role):
    """
    Comprehensive user role validation.
    Returns: (is_authorized, role_data, error_message)
    """
    if not user_role:
        return False, None, "Unable to determine user role"
    
    # Normalize role for comparison
    normalized_role = user_role.lower().strip()
    
    # Check if role is in authorized list
    if normalized_role in AUTHORIZED_ROLES:
        return True, AUTHORIZED_ROLES[normalized_role], None
    
    # Generate specific error message for unauthorized roles
    error_msg = f"Role '{user_role}' is not authorized for system access"
    return False, None, error_msg

def check_login_attempts():
    """Check if user has exceeded maximum login attempts."""
    return st.session_state.login_attempts >= MAX_LOGIN_ATTEMPTS

def reset_login_attempts():
    """Reset login attempt counter."""
    st.session_state.login_attempts = 0

def increment_login_attempts():
    """Increment login attempt counter."""
    st.session_state.login_attempts += 1

# ------------------------
# Enhanced login handler with comprehensive security
# ------------------------
def handle_login(username, password, auth):
    """
    Secure authentication with comprehensive role validation and attempt tracking.
    """
    # Check login attempt limit
    if check_login_attempts():
        st.error("🚫 **Account Temporarily Locked**")
        st.warning(f"""
        Too many failed login attempts ({MAX_LOGIN_ATTEMPTS}).
        Please contact support to unlock your account.
        
        [**Contact Support**](https://vipbusinesscredit.com/)
        """)
        return False
    
    try:
        # Step 1: Authenticate with WordPress
        with st.spinner("🔄 Authenticating credentials..."):
            token = auth.get_token(username, password)
            
        if not token:
            increment_login_attempts()
            remaining = MAX_LOGIN_ATTEMPTS - st.session_state.login_attempts
            st.error(f"❌ **Authentication failed.** {remaining} attempts remaining.")
            return False

        # Step 2: Verify token validity
        with st.spinner("🔄 Verifying token..."):
            if not auth.verify_token(token):
                increment_login_attempts()
                st.error("❌ **Token verification failed.**")
                return False

        # Step 3: Get user role and validate authorization
        with st.spinner("🔄 Validating permissions..."):
            user_role = auth.get_user_role(token)
            is_authorized, role_data, error_msg = validate_user_authorization(user_role)

        if not is_authorized:
            increment_login_attempts()
            st.error("🚫 **Access Denied - Insufficient Privileges**")
            st.warning(f"""
            ### Authorization Failed
            
            **Your Role:** {user_role or 'Unknown'}
            **Error:** {error_msg}
            
            **This system requires one of the following authorized roles:**
            """)
            
            # Display authorized roles
            for role_key, role_info in AUTHORIZED_ROLES.items():
                st.markdown(f"- ✅ **{role_info['name']}** - {role_info['description']}")
            
            st.markdown("""
            **To gain access:**
            - 📞 [**Contact Support**](https://vipbusinesscredit.com/)
            - 🔄 Request role upgrade from your administrator
            - 📧 Verify your account permissions
            """)
            return False

        # Step 4: Grant access and reset attempt counter
        reset_login_attempts()
        st.session_state.authenticated = True
        st.session_state.user_role = user_role.lower()
        st.session_state.token = token
        
        st.success(f"✅ **Authentication Successful!**")
        st.info(f"Welcome, {role_data['name']} - {role_data['description']}")
        st.balloons()
        
        # Show permissions
        with st.expander("🔑 Your Access Permissions"):
            for permission in role_data['permissions']:
                st.markdown(f"✅ {permission.replace('_', ' ').title()}")
        
        st.info("🔄 Redirecting to secure dashboard...")
        st.rerun()
        return True

    except Exception as e:
        increment_login_attempts()
        st.error(f"🚨 **System Error:** {str(e)}")
        st.warning("If this error persists, please contact technical support.")
        return False

# ------------------------
# Secure login page UI
# ------------------------
def login_page():
    """Display secure login interface with comprehensive access control."""
    
    # Check if already authenticated
    if st.session_state.authenticated:
        role_data = AUTHORIZED_ROLES.get(st.session_state.user_role, {})
        st.success(f"✅ Already authenticated as {role_data.get('name', st.session_state.user_role.title())}")
        st.info("🏠 [Access Your Dashboard](Home)")
        
        if st.button("🚪 Logout", type="secondary"):
            for key in ['authenticated', 'user_role', 'token']:
                if key in st.session_state:
                    del st.session_state[key]
            reset_login_attempts()
            st.rerun()
        return

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Logo and title
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.title("💳 VIP Credit Systems")

        st.markdown("### 🔐 Secure System Access")
        st.markdown("**Role-Based Authentication Portal**")

        # Security status indicator
        if check_login_attempts():
            st.error(f"🔒 **Account Locked** - {st.session_state.login_attempts}/{MAX_LOGIN_ATTEMPTS} attempts used")
        else:
            remaining = MAX_LOGIN_ATTEMPTS - st.session_state.login_attempts
            if st.session_state.login_attempts > 0:
                st.warning(f"⚠️ **{st.session_state.login_attempts}/{MAX_LOGIN_ATTEMPTS}** failed attempts - {remaining} remaining")

        # Access requirements notice
        st.info("""
        🔒 **Authorized Access Only**
        
        This system implements strict role-based access control. Only users with 
        **Subscriber** or **Administrator** roles are permitted to access the platform.
        """)

        # Login form
        with st.form("secure_login_form", clear_on_submit=False):
            st.markdown("#### 🔑 Authentication Credentials")
            
            username = st.text_input(
                "Username", 
                placeholder="Enter your WordPress username",
                help="Use your WordPress account username",
                disabled=check_login_attempts()
            )
            
            password = st.text_input(
                "Password", 
                type="password", 
                placeholder="Enter your WordPress password",
                help="Use your WordPress account password",
                disabled=check_login_attempts()
            )

            col_login, col_clear = st.columns([3, 1])
            with col_login:
                login_button = st.form_submit_button(
                    "🔐 Authenticate & Authorize", 
                    use_container_width=True, 
                    type="primary",
                    disabled=check_login_attempts()
                )
            with col_clear:
                clear_button = st.form_submit_button("🗑️ Clear", disabled=check_login_attempts())

            if login_button and username and password and not check_login_attempts():
                auth = initialize_auth()
                handle_login(username, password, auth)

            if clear_button:
                st.rerun()

        # Authorization information
        st.markdown("---")
        st.markdown("### 🔐 Access Authorization Matrix")

        col_auth, col_contact = st.columns([1, 1])
        with col_auth:
            st.markdown("**✅ Authorized Roles:**")
            for role_key, role_data in AUTHORIZED_ROLES.items():
                st.markdown(f"- 🛡️ **{role_data['name']}**")
                st.caption(f"   {role_data['description']}")
        
        with col_contact:
            st.markdown("**📞 Need Access?**")
            st.markdown("""
            - [**Contact Support**](https://vipbusinesscredit.com/)
            - Request role upgrade
            - Verify account status
            """)

        # Security and help information
        st.markdown("---")
        with st.expander("🛡️ Security & Access Information"):
            st.markdown("""
            ### Security Features
            - **Role-Based Access Control (RBAC)** - Only authorized roles can access the system
            - **Token-Based Authentication** - Secure WordPress integration
            - **Attempt Limiting** - Protection against brute force attacks
            - **Session Management** - Secure session handling and timeout
            
            ### Access Requirements
            This system requires one of the following WordPress roles:
            """)
            
            for role_key, role_data in AUTHORIZED_ROLES.items():
                st.markdown(f"""
                **{role_data['name']} ({role_data['access_level']} access)**
                - Description: {role_data['description']}
                - Permissions: {', '.join(role_data['permissions'])}
                """)
            
            st.markdown("""
            ### Troubleshooting
            **If you're unable to access the system:**
            1. Verify your WordPress credentials are correct
            2. Confirm your account role with your administrator
            3. Ensure your account is active and not suspended
            4. Contact support if you believe you should have access
            
            **Account locked?** Contact support to reset your login attempts.
            """)

# ------------------------
# Run the secure login page
# ------------------------
login_page()

