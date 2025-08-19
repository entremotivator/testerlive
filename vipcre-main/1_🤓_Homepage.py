import streamlit as st
from wordpress_auth import WordpressAuth

# ------------------------
# Page Configuration
# ------------------------
st.set_page_config(
    page_title="VIP Credit Systems",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------
# Authentication Functions
# ------------------------
def initialize_auth():
    """Initialize the WordpressAuth instance with secrets."""
    try:
        base_url = st.secrets["general"]["base_url"]
        api_key = st.secrets["general"]["api_key"]
        return WordpressAuth(api_key=api_key, base_url=base_url)
    except KeyError as e:
        st.error(f"❌ Missing secret configuration: {e}")
        st.info("Please ensure your secrets.toml file contains the required WordPress configuration.")
        st.stop()
    except Exception as e:
        st.error(f"🔥 Authentication initialization error: {str(e)}")
        st.stop()

def check_user_role_access(role):
    """Check if user role has access to the system"""
    allowed_roles = ['subscriber', 'administrator']
    return role in allowed_roles

# ------------------------
# Configuration and User Role Management
# ------------------------

# Define user roles here - REQUIRED for access control
USER_ROLES = {
    # Standard WordPress Roles
    'admin': 'administrator',
    'super_admin': 'super_admin',
    'editor_user': 'editor',
    'author_user': 'author',
    'contributor_user': 'contributor',
    'subscriber_user': 'subscriber',
    
    # WooCommerce Roles
    'shop_manager': 'shop_manager',
    'customer_user': 'customer',  # Will be denied access
    
    # Custom Business Roles
    'business_owner': 'administrator',
    'manager': 'editor',
    'employee': 'subscriber',
    'vip_member': 'subscriber',
    'premium_user': 'subscriber',
    
    # Support and Service Roles  
    'support_agent': 'contributor',
    'moderator': 'editor',
    'content_creator': 'author',
    
    # Membership Plugin Roles
    'member': 'subscriber',
    'premium_member': 'subscriber',
    'gold_member': 'subscriber',
    'platinum_member': 'administrator',
    
    # Learning Management System Roles
    'instructor': 'editor',
    'student': 'subscriber',
    'course_admin': 'administrator',
    
    # Real Estate Roles
    'agent': 'contributor',
    'broker': 'editor',
    'property_manager': 'subscriber',
    
    # E-commerce Extended Roles
    'vendor': 'contributor',
    'affiliate': 'subscriber',
    'reseller': 'subscriber',
    
    # Organization Roles
    'ceo': 'administrator',
    'cto': 'administrator', 
    'marketing_manager': 'editor',
    'sales_rep': 'contributor',
    'accountant': 'subscriber',
    
    # Example users - Replace with your actual usernames
    'john_admin': 'administrator',
    'jane_editor': 'editor',
    'mike_subscriber': 'subscriber',
    'sarah_customer': 'customer',  # Will be denied access
}

def get_user_role_from_config(username):
    """Get user role from configuration - NO DEFAULT ROLE."""
    return USER_ROLES.get(username.lower(), None)

def get_user_role_from_auth(auth, token, username):
    """Get user role from WordPress auth with NO default fallback."""
    try:
        user_role = None
        
        # Try the get_user_role method if it exists
        if hasattr(auth, 'get_user_role'):
            user_role = auth.get_user_role(token)
        
        # Fallback: Try get_user_info method if available
        elif hasattr(auth, 'get_user_info'):
            user_info = auth.get_user_info(token)
            if isinstance(user_info, dict) and 'role' in user_info:
                user_role = user_info.get('role')
        
        # Fallback: Try user_data method if available
        elif hasattr(auth, 'user_data'):
            user_data = auth.user_data(token)
            if isinstance(user_data, dict) and 'role' in user_data:
                user_role = user_data.get('role')
        
        # If WordPress auth didn't provide role, check configuration
        if not user_role:
            user_role = get_user_role_from_config(username)
        
        # Return role only if explicitly found, otherwise None
        return user_role if user_role else None
            
    except Exception as e:
        st.error(f"🔥 Error determining user role: {str(e)}")
        return None

def handle_login(username, password, auth):
    """Handle user login process with strict role-based access control."""
    if not username or not password:
        st.error("❌ Please enter both username and password")
        return False
    
    try:
        with st.spinner("🔐 Authenticating..."):
            token = auth.get_token(username, password)
            
            if token and auth.verify_token(token):
                user_role = get_user_role_from_auth(auth, token, username)
                
                # Strict role checking - NO access without explicit role
                if not user_role:
                    st.error("🚫 **Access Denied**: No role assigned to this user.")
                    st.warning("Please contact an administrator to assign a role to your account.")
                    st.info("📝 **Note**: Add user roles in the USER_ROLES configuration if WordPress doesn't provide role information.")
                    return False
                
                # Check if user role is allowed
                elif check_user_role_access(user_role):
                    # Store authentication data
                    st.session_state.authenticated = True
                    st.session_state.token = token
                    st.session_state.user_role = user_role
                    st.session_state.username = username
                    
                    st.success(f"✅ Login successful! Welcome, {user_role.title()}!")
                    st.rerun()
                    return True
                    
                elif user_role == 'customer':
                    st.error("🚫 **Access Denied**: Customers are not allowed to access this system.")
                    st.warning("Please contact an administrator if you need access.")
                    return False
                    
                else:
                    st.error(f"🚫 **Access Denied**: Your role '{user_role}' is not authorized.")
                    st.info("Only subscribers and administrators can access this system.")
                    return False
            else:
                st.error("❌ **Authentication Failed**: Invalid credentials. Please try again.")
                return False
                
    except Exception as e:
        st.error(f"🔥 **Login Error**: {str(e)}")
        st.info("Please check your connection and try again.")
        return False

# ------------------------
# Session State Initialization
# ------------------------
def init_session_state():
    """Initialize session state variables"""
    if 'auth' not in st.session_state:
        st.session_state.auth = initialize_auth()
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None

# ------------------------
# Login Sidebar
# ------------------------
def render_login_sidebar():
    """Render the login form in the sidebar"""
    with st.sidebar:
        st.header("🔐 Login")
        
        with st.form(key='login_form'):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button("🔑 Login", use_container_width=True)
        
        if login_button:
            handle_login(username, password, st.session_state.auth)

        # Access control information
        st.markdown("---")
        st.markdown("**🛡️ Access Control:**")
        st.success("✅ Administrators - Full Access")
        st.info("👤 Subscribers - System Access") 
        st.error("❌ Customers - Access Denied")
        st.warning("⚠️ Users without assigned roles - Access Denied")
        
        # Configuration info
        st.markdown("---")
        st.markdown("**⚙️ Role Configuration:**")
        if USER_ROLES:
            st.info(f"📋 {len(USER_ROLES)} users configured in USER_ROLES")
        else:
            st.warning("🔧 No users configured in USER_ROLES - configure roles in code")
        
        # Sign-up link
        st.markdown("---")
        st.markdown("### 📝 Need an Account?")
        st.markdown("[**Sign Up Here**](https://vipbusinesscredit.com/)")

# ------------------------
# Authenticated Sidebar
# ------------------------
def render_authenticated_sidebar():
    """Render sidebar content for authenticated users"""
    with st.sidebar:
        # Logo
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.markdown("### 💳 VIP Credit")
        
        # User info
        st.markdown("---")
        st.success(f"👋 Welcome, {st.session_state.username}!")
        st.info(f"🎭 Role: {st.session_state.user_role.title()}")
        
        # Navigation prompt
        st.markdown("---")
        st.markdown("### 🧭 Navigation")
        st.info("Select a page from the main navigation above.")
        
        # Logout button
        st.markdown("---")
        if st.button("🔓 Logout", use_container_width=True):
            # Clear session state
            for key in ['authenticated', 'token', 'user_role', 'username']:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("👋 Logged out successfully!")
            st.rerun()

# ------------------------
# Main Content
# ------------------------
def render_main_content():
    """Render the main VIP Credit Systems content"""
    
    # Main layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Logo at top
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.markdown("# 💳 VIP Credit Systems")

        # App Header
        st.title("VIP Credit Systems")
        st.subheader("Your Comprehensive Credit Management Solution")

        # User-specific welcome message
        if st.session_state.user_role == 'administrator':
            st.success("🔓 **Administrator Dashboard** - You have full access to all system features")
        else:
            st.info("📊 **Credit Management Dashboard** - Access to all credit tools and insights")

        # Introduction
        st.markdown("""
        Welcome to **VIP Credit Systems**, where managing your credit has never been easier. Our system provides a wide range of tools and insights to help you understand and optimize your credit profile. Below is a detailed list of features we offer to assist you in taking control of your financial future.
        """)

        # Feature Categories with Enhanced Styling
        st.markdown("---")
        st.markdown("## 🎯 Available Features")
        
        # Credit Overview Section
        with st.expander("📊 **Credit Overview**", expanded=True):
            st.markdown("""
            - 📊 **Credit Score Overview** - Comprehensive view of your current credit score
            - 💳 **Credit Utilization** - Track your credit usage across all accounts
            - 🗓️ **Payment History** - Detailed payment tracking and history
            - 📑 **Credit Report Summary** - Summarized view of your credit report
            """)

        # Account Management Section
        with st.expander("🔧 **Account Management**"):
            st.markdown("""
            - 🔍 **Credit Inquiries** - Monitor hard and soft credit inquiries
            - 🎯 **Credit Limits** - Track and manage your credit limits
            - ⚖️ **Debt-to-Income Ratio** - Calculate and monitor your DTI ratio
            - 💰 **Loan and Credit Card Balances** - Overview of all outstanding balances
            """)

        # Analytics and Insights Section
        with st.expander("📈 **Analytics and Insights**"):
            st.markdown("""
            - ⏳ **Account Age** - Track the age of your credit accounts
            - 💵 **Monthly Payments** - Monitor your monthly payment obligations
            - 📂 **Credit Accounts Breakdown** - Detailed breakdown by account type
            - 🏆 **Top 5 Highest Balances** - Identify accounts with highest balances
            """)

        # Transactions and Payments Section
        with st.expander("💳 **Transactions and Payments**"):
            st.markdown("""
            - 📝 **Top 5 Recent Transactions** - Track your latest transactions
            - 📅 **Upcoming Payments** - Never miss a payment with our calendar
            - 🔄 **Credit Utilization by Account Type** - Utilization breakdown
            - 📊 **Average Payment History** - Historical payment performance
            """)

        # Trends and Forecasting Section
        with st.expander("📊 **Trends and Forecasting**"):
            st.markdown("""
            - 📈 **Credit Score Trend** - Track your credit score over time
            - 💸 **Monthly Spending Trend** - Monitor spending patterns
            - 📉 **Credit Score vs. Credit Utilization** - Correlation analysis
            - 📅 **Debt Repayment Schedule** - Plan your debt payoff strategy
            """)

        # Credit Management Tools Section
        with st.expander("🛠️ **Credit Management Tools**"):
            st.markdown("""
            - 🆕 **New Credit Accounts** - Track recently opened accounts
            - 🧠 **Credit Score Impact Simulation** - Predict score changes
            - 📉 **Debt Reduction Plan** - Create personalized debt reduction strategies
            - 💡 **Credit Score Improvement Tips** - Actionable improvement advice
            """)

        # Admin-only features
        if st.session_state.user_role == 'administrator':
            with st.expander("🔐 **Administrator Tools**", expanded=True):
                st.markdown("""
                - 👥 **User Management** - Manage system users and permissions
                - 📊 **System Analytics** - Monitor system usage and performance
                - ⚙️ **System Configuration** - Configure system settings
                - 🔍 **Audit Logs** - Review system activity logs
                """)

        # Customization and Tools Section
        with st.expander("⚙️ **Customization and Tools**"):
            st.markdown("""
            - ⚠️ **Alerts and Recommendations** - Personalized credit alerts
            - ✏️ **Edit Credit Info** - Update your credit information
            - 📤 **Export Data** - Export your data for external analysis
            - 🔔 **Notification Settings** - Customize your alert preferences
            """)

        # Call to Action
        st.markdown("---")
        st.markdown("### 🚀 Get Started")
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.info("📊 **Monitor** your credit score and accounts")
        with col_b:
            st.success("📈 **Improve** your credit with our tools")
        with col_c:
            st.warning("🎯 **Achieve** your financial goals")

        # Conclusion
        st.markdown("""
        ---
        **Ready to take control of your credit?** Explore these features and more in the VIP Credit Systems app. Whether you are looking to improve your credit score, manage your debts, or simply stay on top of your financial health, we've got you covered. Start making informed financial decisions today!
        """)

# ------------------------
# Unauthenticated Content
# ------------------------
def render_unauthenticated_content():
    """Render content for users who are not logged in"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Logo
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.markdown("# 💳 VIP Credit Systems")
        
        st.title("VIP Credit Systems")
        st.subheader("Your Comprehensive Credit Management Solution")
        
        # Login prompt
        st.info("🔐 **Please log in to access the VIP Credit Systems.**")
        
        # Features preview
        st.markdown("""
        ### What You'll Get Access To:
        
        ✅ **Real-time Credit Monitoring**  
        ✅ **Comprehensive Credit Analytics**  
        ✅ **Personalized Improvement Plans**  
        ✅ **Payment Tracking & Alerts**  
        ✅ **Debt Management Tools**  
        ✅ **Credit Score Simulators**  
        
        ---
        
        🔑 **Use the login form in the sidebar to get started!**
        """)
        
        # Access information
        st.warning("""
        **Important Access Requirements:**
        - This system is available to subscribers and administrators only
        - Customers do not have access to this platform
        - Users must have an explicitly assigned role (no default roles)
        - Contact an administrator if you need role assignment
        """)
        
        # Role configuration note
        if not USER_ROLES:
            st.info("""
            **For Developers:** Configure user roles in the USER_ROLES dictionary 
            in the code if WordPress doesn't provide role information automatically.
            """)

# ------------------------
# Main Application
# ------------------------
def main():
    """Main application entry point"""
    # Initialize session state
    init_session_state()
    
    # Verify token if user claims to be authenticated
    if st.session_state.authenticated:
        try:
            if not st.session_state.auth.verify_token(st.session_state.token):
                # Token is invalid, reset authentication
                for key in ['authenticated', 'token', 'user_role', 'username']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.warning("🔄 Session expired. Please log in again.")
                st.rerun()
        except Exception as e:
            # Error verifying token, reset authentication
            for key in ['authenticated', 'token', 'user_role', 'username']:
                if key in st.session_state:
                    del st.session_state[key]
            st.error(f"❌ Authentication error: {str(e)}. Please log in again.")
            st.rerun()
    
    # Render appropriate content based on authentication status
    if st.session_state.authenticated:
        render_authenticated_sidebar()
        render_main_content()
    else:
        render_login_sidebar()
        render_unauthenticated_content()

# ------------------------
# Run Application
# ------------------------
if __name__ == "__main__":
    main()
