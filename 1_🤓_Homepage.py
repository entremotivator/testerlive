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
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'token' not in st.session_state:
    st.session_state.token = None

# Security configuration - ONLY these roles are allowed
AUTHORIZED_ROLES = {
    'subscriber': {
        'name': 'Subscriber',
        'access_level': 'standard',
        'description': 'Credit dashboard access'
    },
    'administrator': {
        'name': 'Administrator', 
        'access_level': 'full',
        'description': 'Full system privileges'
    }
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

def validate_user_access(user_role):
    """
    Validate if user role has access to the system.
    Returns tuple: (is_authorized, role_info)
    """
    if not user_role:
        return False, None
    
    normalized_role = user_role.lower().strip()
    
    if normalized_role in AUTHORIZED_ROLES:
        return True, AUTHORIZED_ROLES[normalized_role]
    
    return False, None

def handle_login(username, password, auth):
    """Handle user login with comprehensive role validation."""
    try:
        # Step 1: Get authentication token
        token = auth.get_token(username, password)
        if not token:
            st.sidebar.error("❌ Invalid credentials")
            return False
        
        # Step 2: Verify token
        if not auth.verify_token(token):
            st.sidebar.error("❌ Token verification failed")
            return False
        
        # Step 3: Get and validate user role
        user_role = auth.get_user_role(token)
        is_authorized, role_info = validate_user_access(user_role)
        
        if not is_authorized:
            st.sidebar.error("🚫 **Access Denied**")
            st.sidebar.warning(f"""
            **Unauthorized Role: {user_role or 'Unknown'}**
            
            **System Access is Limited To:**
            - ✅ Subscriber accounts
            - ✅ Administrator accounts
            
            **Your role is not authorized for this system.**
            
            [**Request Access**](https://vipbusinesscredit.com/)
            """)
            return False
        
        # Step 4: Grant access
        st.session_state.authenticated = True
        st.session_state.user_role = user_role.lower()
        st.session_state.token = token
        st.sidebar.success(f"✅ Welcome, {role_info['name']}!")
        st.sidebar.info(f"Access Level: {role_info['description']}")
        st.rerun()
        return True
            
    except Exception as e:
        st.sidebar.error(f"Authentication error: {str(e)}")
        return False

def logout():
    """Handle user logout and clear session."""
    for key in ['authenticated', 'user_role', 'token']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def sidebar_content():
    """Handle sidebar content with security-focused UI."""
    with st.sidebar:
        # Logo
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.markdown("### 💳 VIP Credit")
        
        if not st.session_state.authenticated:
            # Login Form
            st.markdown("### 🔐 Secure Login")
            
            # Security notice
            st.info("🔒 Restricted Access System")
            
            with st.form("sidebar_login_form"):
                username = st.text_input("Username", placeholder="WordPress username")
                password = st.text_input("Password", type="password", placeholder="WordPress password")
                login_button = st.form_submit_button("🔐 Authenticate", use_container_width=True)
                
                if login_button and username and password:
                    with st.spinner("Validating credentials and permissions..."):
                        auth = initialize_auth()
                        handle_login(username, password, auth)
            
            # Access control information
            st.markdown("---")
            st.markdown("**🔐 Access Control**")
            
            with st.expander("View Authorized Roles"):
                for role_key, role_data in AUTHORIZED_ROLES.items():
                    st.markdown(f"✅ **{role_data['name']}** - {role_data['description']}")
                
                st.markdown("❌ **All other roles** - Access denied")
            
            st.markdown("[📞 Request Access](https://vipbusinesscredit.com/)")
                
        else:
            # Authenticated user info
            role_info = AUTHORIZED_ROLES.get(st.session_state.user_role, {})
            st.success(f"👤 {role_info.get('name', st.session_state.user_role.title())}")
            st.caption(f"🔑 {role_info.get('description', 'System access')}")
            
            if st.button("🚪 Secure Logout", use_container_width=True):
                logout()
            
            st.markdown("---")
            st.info("📌 Navigate using the menu above")

def main_content():
    """Display main content with role-based features."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Main logo
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.title("💳 VIP Credit Systems")

        st.title("VIP Credit Systems")
        st.subheader("Secure Credit Management Platform")

        if st.session_state.authenticated:
            # Role-specific welcome
            role_info = AUTHORIZED_ROLES.get(st.session_state.user_role, {})
            
            if st.session_state.user_role == 'administrator':
                st.success("🛠️ **Administrator Dashboard** - Full system access granted")
            elif st.session_state.user_role == 'subscriber':
                st.success("📊 **Subscriber Dashboard** - Credit monitoring access granted")

            st.write(f"""
            Welcome to your secure **VIP Credit Systems** dashboard. You are logged in with 
            **{role_info.get('name', 'authorized')}** privileges, providing you with 
            {role_info.get('description', 'system access')}.
            """)

            # Feature sections based on role
            st.markdown("## 🎯 Your Available Features")
            
            # Core features for all authorized users
            with st.expander("📊 Credit Monitoring", expanded=True):
                st.markdown("""
                - **Real-time Credit Score Tracking** - Monitor score changes instantly
                - **Credit Utilization Analysis** - Optimize your credit usage ratios
                - **Payment History Dashboard** - Track payment patterns and trends
                - **Credit Report Integration** - Comprehensive report analysis
                """)

            with st.expander("🔧 Account Management"):
                st.markdown("""
                - **Credit Inquiry Monitoring** - Track hard and soft credit pulls
                - **Credit Limit Optimization** - Maximize available credit efficiently
                - **Debt-to-Income Calculator** - Monitor and improve DTI ratios
                - **Balance Management** - Strategic balance optimization
                """)

            # Advanced features
            if st.session_state.user_role == 'administrator':
                with st.expander("🛠️ Administrator Tools"):
                    st.markdown("""
                    - **User Management** - Manage system access and permissions
                    - **System Configuration** - Configure platform settings
                    - **Advanced Analytics** - Deep-dive reporting and insights
                    - **Security Monitoring** - Track system access and usage
                    """)

            with st.expander("📈 Analytics & Insights"):
                st.markdown("""
                - **Credit History Analysis** - Track account age and history impact
                - **Payment Pattern Analytics** - Identify optimization opportunities
                - **Account Performance Metrics** - Detailed account breakdowns
                - **Predictive Modeling** - Forecast credit score changes
                """)

            # Call to action
            st.markdown("---")
            st.success("""
            🚀 **Your Dashboard is Ready** 
            
            Use the navigation menu above to access your personalized credit management tools 
            and start optimizing your financial profile with confidence.
            """)
            
        else:
            # Non-authenticated content
            st.warning("🔐 **Secure Access Required**")
            st.write("""
            **VIP Credit Systems** is a secure, role-based credit management platform. 
            Access is restricted to authorized personnel with proper credentials and permissions.
            """)

            # System overview for non-authenticated users
            st.markdown("## 🔒 Secure Platform Overview")
            
            col_security, col_features = st.columns(2)
            
            with col_security:
                st.markdown("""
                ### 🛡️ Security Features
                - Role-based access control
                - Encrypted data transmission
                - Secure authentication system
                - Audit trail monitoring
                """)
            
            with col_features:
                st.markdown("""
                ### 📊 Platform Capabilities
                - Real-time credit monitoring
                - Advanced analytics dashboard
                - Comprehensive reporting
                - Predictive insights
                """)

            # Access requirements
            st.markdown("---")
            st.error("""
            🚫 **Access Restricted** 
            
            This platform requires **Subscriber** or **Administrator** credentials.
            Unauthorized access attempts are logged and monitored.
            
            [**Contact Support for Access**](https://vipbusinesscredit.com/)
            """)

# Main application logic
sidebar_content()
main_content()

