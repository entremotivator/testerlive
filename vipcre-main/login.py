import streamlit as st
from wordpress_auth import WordpressAuth

# ------------------------
# Page Configuration
# ------------------------
st.set_page_config(
    page_title="WordPress Login System",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------
# User Role Configuration
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

def check_user_role_access(role):
    """Check if user role has access to the system"""
    if not role:
        return False
    
    # Define allowed roles for system access
    allowed_roles = [
        # WordPress Standard Roles (allowed)
        'administrator',
        'super_admin', 
        'editor',
        'author',
        'contributor',
        'subscriber',
        
        # WooCommerce Roles (selective)
        'shop_manager',  # Allowed - business management
        # 'customer' - DENIED ACCESS
        
        # Custom Business Roles (allowed)
        'business_owner',
        'manager',
        'employee',
        'vip_member',
        'premium_user',
        
        # Support Roles (allowed)
        'support_agent',
        'moderator',
        'content_creator',
        
        # Membership Roles (allowed)
        'member',
        'premium_member',
        'gold_member',
        'platinum_member',
        
        # LMS Roles (allowed)
        'instructor',
        'student',
        'course_admin',
        
        # Real Estate Roles (allowed)
        'agent',
        'broker',
        'property_manager',
        
        # E-commerce Extended Roles (allowed)
        'vendor',
        'affiliate',
        'reseller',
        
        # Organization Roles (allowed)
        'ceo',
        'cto',
        'marketing_manager',
        'sales_rep',
        'accountant'
    ]
    
    # Explicitly denied roles
    denied_roles = [
        'customer',  # Primary denied role
        'guest',
        'pending',
        'blocked',
        'suspended'
    ]
    
    # Check if role is explicitly denied
    if role in denied_roles:
        return False
        
    # Check if role is in allowed list
    return role in allowed_roles

# ------------------------
# Configuration Sidebar
# ------------------------
def get_user_input():
    """Get WordPress configuration from sidebar"""
    with st.sidebar:
        st.title("⚙️ Configuration Settings")
        st.markdown("---")
        
        wordpress_url = st.text_input(
            "WordPress Site URL", 
            placeholder="https://yourwordpressurl.com",
            help="Enter your WordPress site URL"
        )
        
        api_key_input = st.text_input(
            "API Key", 
            type='password',
            help="Enter your WordPress API key"
        )
        
        st.markdown("---")
        st.markdown("**🛡️ Access Control:**")
        st.success("✅ Administrators, Super Admins - Full Access")
        st.info("✏️ Editors, Managers, Shop Managers - Content Management")
        st.warning("📝 Authors, Contributors, Instructors - Content Creation")
        st.info("👤 Subscribers, Members, Students - Content Access")
        st.error("❌ Customers - Access Denied")
        st.error("⛔ Guests, Pending, Blocked - Access Denied")
        
        # Configuration info
        st.markdown("---")
        st.markdown("**⚙️ Role Configuration:**")
        if USER_ROLES:
            st.info(f"📋 {len(USER_ROLES)} users configured in USER_ROLES")
            
            # Show role distribution
            role_counts = {}
            for username, role in USER_ROLES.items():
                role_counts[role] = role_counts.get(role, 0) + 1
            
            st.markdown("**Role Distribution:**")
            for role, count in sorted(role_counts.items()):
                if role == 'customer':
                    st.error(f"❌ {role}: {count} users")
                elif role in ['administrator', 'super_admin']:
                    st.success(f"🔐 {role}: {count} users")
                elif role in ['editor', 'manager', 'shop_manager']:
                    st.info(f"✏️ {role}: {count} users") 
                else:
                    st.text(f"👤 {role}: {count} users")
        else:
            st.warning("🔧 No users configured in USER_ROLES - configure roles in code")
        
        return wordpress_url, api_key_input

# ------------------------
# Main Dashboard
# ------------------------
def main_page(user_role, username=None):
    """Main page content based on user role"""
    st.title(f"🎯 Welcome, {user_role.capitalize()}!")
    
    if username:
        st.subheader(f"Logged in as: {username}")
    
    col1, col2, col3 = st.columns(3)
    
    # Administrator and Super Admin roles
    if user_role in ['administrator', 'super_admin', 'business_owner', 'ceo', 'cto', 'course_admin', 'platinum_member']:
        with col1:
            st.metric("Access Level", "Full Admin", "100%")
        with col2:
            st.metric("Permissions", "All Features", "✅")
        with col3:
            st.metric("Status", "Active", "🟢")
            
        st.markdown("---")
        st.success("🔓 **Administrator Access Granted**")
        st.write("You have full access to all administrative features:")
        
        # Admin-specific features
        tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "User Management", "Settings", "System Admin"])
        
        with tab1:
            st.write("📊 **Admin Dashboard**")
            st.info("Access to all system metrics and analytics")
            st.markdown("""
            - System health monitoring
            - User activity reports
            - Performance analytics
            - Error tracking
            - Revenue and sales reports
            """)
            
        with tab2:
            st.write("👥 **User Management**")
            st.info("Manage user accounts and permissions")
            st.markdown("""
            - Add/remove users
            - Assign user roles
            - Monitor user activity
            - Manage access permissions
            - Bulk user operations
            """)
            
        with tab3:
            st.write("⚙️ **System Settings**")
            st.info("Configure system-wide settings")
            st.markdown("""
            - Application configuration
            - Security settings
            - Integration management
            - Backup and restore
            - Payment gateway settings
            """)
            
        with tab4:
            st.write("🔧 **System Administration**")
            st.info("Advanced system administration tools")
            st.markdown("""
            - Role configuration management
            - WordPress integration settings
            - API key management
            - System maintenance
            - Database management
            """)
    
    # Editor and Manager roles
    elif user_role in ['editor', 'manager', 'shop_manager', 'moderator', 'broker', 'marketing_manager']:
        with col1:
            st.metric("Access Level", "Editor/Manager", "80%")
        with col2:
            st.metric("Permissions", "Content & Users", "✅")
        with col3:
            st.metric("Status", "Active", "🟢")
            
        st.markdown("---")
        st.info("✏️ **Editor/Manager Access Granted**")
        st.write("You have access to content management and user oversight:")
        
        tab1, tab2, tab3 = st.tabs(["Content Management", "User Oversight", "Reports"])
        
        with tab1:
            st.write("📝 **Content Management**")
            st.success("Create, edit, and publish content")
            st.markdown("""
            - Create and edit all content
            - Publish and manage posts
            - Media library access
            - SEO optimization tools
            """)
            
        with tab2:
            st.write("👥 **User Oversight**")
            st.success("Limited user management capabilities")
            st.markdown("""
            - View user profiles
            - Monitor user activity
            - Moderate user content
            - Basic user support
            """)
            
        with tab3:
            st.write("📊 **Reports & Analytics**")
            st.success("Access to performance reports")
            st.markdown("""
            - Content performance metrics
            - User engagement reports
            - Traffic analytics
            - Conversion tracking
            """)
    
    # Author and Contributor roles
    elif user_role in ['author', 'contributor', 'content_creator', 'instructor', 'agent', 'vendor', 'sales_rep', 'support_agent']:
        with col1:
            st.metric("Access Level", "Content Creator", "60%")
        with col2:
            st.metric("Permissions", "Create Content", "⚠️")
        with col3:
            st.metric("Status", "Active", "🟢")
            
        st.markdown("---")
        st.warning("📝 **Content Creator Access**")
        st.write("You can create and manage your own content:")
        
        tab1, tab2 = st.tabs(["My Content", "Tools"])
        
        with tab1:
            st.write("📄 **My Content**")
            st.success("Create and edit your own content")
            st.markdown("""
            - Write and edit your posts
            - Upload media files
            - Schedule publications
            - Track content performance
            """)
            
        with tab2:
            st.write("🛠️ **Available Tools**")
            st.success("Content creation and management tools")
            st.markdown("""
            - Rich text editor
            - Image editing tools
            - SEO suggestions
            - Publishing calendar
            """)
    
    # Subscriber and Member roles
    else:  # All other allowed roles
        role_display = {
            'subscriber': 'Subscriber',
            'employee': 'Employee', 
            'vip_member': 'VIP Member',
            'premium_user': 'Premium User',
            'member': 'Member',
            'premium_member': 'Premium Member',
            'gold_member': 'Gold Member',
            'student': 'Student',
            'property_manager': 'Property Manager',
            'affiliate': 'Affiliate',
            'reseller': 'Reseller',
            'accountant': 'Accountant'
        }.get(user_role, user_role.replace('_', ' ').title())
        
        with col1:
            st.metric("Access Level", role_display, "40%")
        with col2:
            st.metric("Permissions", "View Content", "ℹ️")
        with col3:
            st.metric("Status", "Active", "🟢")
            
        st.markdown("---")
        st.info(f"📖 **{role_display} Access Granted**")
        st.write("You have access to subscriber content and features:")
        
        # Subscriber-specific features
        tab1, tab2, tab3 = st.tabs(["Content", "Profile", "Support"])
        
        with tab1:
            st.write("📚 **Available Content**")
            st.success("Access to your content library")
            st.markdown("""
            - Premium content library
            - Exclusive tutorials and guides
            - Member-only resources
            - Downloadable materials
            - Video content library
            """)
            
        with tab2:
            st.write("👤 **Profile Management**")
            st.success("Manage your account and preferences")
            st.markdown("""
            - Update profile information
            - Manage notification preferences
            - View subscription/membership status
            - Account settings and security
            - Activity history
            """)
            
        with tab3:
            st.write("🎧 **Support & Community**")
            st.success("Get help and connect with others")
            st.markdown("""
            - Submit support tickets
            - Access knowledge base
            - Community forums access
            - FAQ and help documentation
            - Live chat support
            """)

# ------------------------
# Login Page
# ------------------------
def login_page(auth):
    """Login form and authentication handling"""
    st.title("🔐 WordPress Login")
    st.markdown("Please enter your credentials to access the system")
    
    # Create columns for better layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form(key='login_form'):
            st.markdown("### Login Form")
            
            username_input = st.text_input(
                "Username",
                placeholder="Enter your username",
                help="Your WordPress username"
            )
            
            password_input = st.text_input(
                "Password", 
                type='password',
                placeholder="Enter your password",
                help="Your WordPress password"
            )
            
            submit_button = st.form_submit_button(
                "🔑 Log In",
                use_container_width=True
            )
            
            if submit_button:
                if not username_input or not password_input:
                    st.error("❌ Please enter both username and password")
                    return
                
                with st.spinner("🔐 Authenticating..."):
                    try:
                        # Attempt to get token
                        token = auth.get_token(username_input, password_input)
                        
                        if token and auth.verify_token(token):
                            user_role = get_user_role_from_auth(auth, token, username_input)
                            
                            # Strict role checking - NO access without explicit role
                            if not user_role:
                                st.error("🚫 **Access Denied**: No role assigned to this user.")
                                st.warning("Please contact an administrator to assign a role to your account.")
                                st.info("📝 **Note**: User roles must be configured in the system.")
                                return
                            
                            # Check if user role is allowed
                            elif check_user_role_access(user_role):
                                st.session_state['token'] = token
                                st.session_state['role'] = user_role
                                st.session_state['username'] = username_input
                                st.session_state['authenticated'] = True
                                st.success(f"✅ Logged in successfully as {user_role}!")
                                st.rerun()
                                
                            elif user_role == 'customer':
                                st.error("🚫 **Access Denied**: Customers are not allowed to access this system.")
                                st.warning("Please contact an administrator if you need access.")
                                
                            else:
                                st.error(f"🚫 **Access Denied**: Your role '{user_role}' is not authorized.")
                                st.info("Only subscribers and administrators can access this system.")
                                
                        else:
                            st.error("❌ **Authentication Failed**: Invalid credentials. Please try again.")
                            
                    except Exception as e:
                        st.error(f"🔥 **Login Error**: {str(e)}")
                        st.info("Please check your WordPress URL and API key configuration.")

# ------------------------
# Access Denied Page
# ------------------------
def access_denied_page():
    """Page shown when access is denied"""
    st.title("🚫 Access Denied")
    st.error("You do not have permission to access this application.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        ### Authorized Users Only
        
        This application is restricted to:
        - **Administrators**: Full system access
        - **Subscribers**: Limited content access
        
        **Not Permitted:**
        - **Customers**: Access denied
        - **Users without assigned roles**: Access denied
        
        If you believe this is an error, please contact your system administrator.
        """)

# ------------------------
# Logout Functionality
# ------------------------
def logout():
    """Handle user logout"""
    if 'token' in st.session_state:
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👤 User Session")
            st.success(f"Logged in as: **{st.session_state.get('username', 'User')}**")
            st.info(f"Role: **{st.session_state.get('role', 'Unknown').title()}**")
            
            if st.button("🔓 Log Out", use_container_width=True):
                # Clear session state
                for key in ['token', 'role', 'username', 'authenticated']:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.success("👋 Logged out successfully.")
                st.rerun()

# ------------------------
# Session State Management
# ------------------------
def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

# ------------------------
# Main Application Logic
# ------------------------
def main():
    """Main application entry point"""
    init_session_state()
    
    # Get configuration from sidebar
    wordpress_url, api_key_input = get_user_input()
    
    # Check if configuration is provided
    if wordpress_url and api_key_input:
        try:
            # Initialize WordPress authentication
            auth = WordpressAuth(api_key=api_key_input, base_url=wordpress_url)
            
            # Check if user is logged in and token is valid
            if (st.session_state.get('authenticated', False) and
                'token' in st.session_state and 
                'role' in st.session_state):
                
                # Verify token is still valid
                try:
                    if auth.verify_token(st.session_state['token']):
                        # User is authenticated - show main page
                        username = st.session_state.get('username', 'User')
                        main_page(st.session_state['role'], username)
                        logout()
                    else:
                        # Token invalid - clear session
                        for key in ['token', 'role', 'username', 'authenticated']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.warning("🔄 Session expired. Please log in again.")
                        login_page(auth)
                except Exception as e:
                    # Error verifying token - clear session
                    for key in ['token', 'role', 'username', 'authenticated']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.error(f"❌ Session verification error: {str(e)}. Please log in again.")
                    login_page(auth)
                
            else:
                # User not authenticated - show login page
                login_page(auth)
                
        except Exception as e:
            st.error(f"🔥 **Configuration Error**: {str(e)}")
            st.info("Please check your WordPress URL and API key in the sidebar.")
            
    else:
        # Configuration not provided
        st.warning("⚠️ **Configuration Required**")
        st.info("Please enter your WordPress site URL and API key in the sidebar to continue.")
        
        # Show information about the app
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            ### WordPress Authentication System
            
            This application provides secure access control with WordPress integration.
            
            **🔐 Security Features:**
            - Secure WordPress authentication
            - Strict role-based access control
            - No default role assignments
            - Customer access restriction
            - Token-based session management
            
            **📊 Dashboards:**
            - Admin dashboard with full system access
            - Subscriber dashboard with limited access
            - Role-specific feature sets
            
            **⚙️ Setup Instructions:**
            1. Enter your WordPress site URL in the sidebar
            2. Provide your API key for authentication
            3. Configure user roles in the USER_ROLES dictionary
            4. Log in with your WordPress credentials
            
            **🎯 Access Levels:**
            - **Administrators**: Full system access + admin tools
            - **Subscribers**: Content access + profile management
            - **Customers**: Access denied
            - **No Role Assigned**: Access denied
            
            **⚠️ Important:** Users must have explicitly assigned roles. 
            No default roles are granted for security.
            """)
            
            # Role configuration status
            st.markdown("---")
            st.markdown("### 🔧 Configuration Status")
            if USER_ROLES:
                st.success(f"✅ {len(USER_ROLES)} users configured in USER_ROLES")
                st.info("Users with configured roles can access the system")
            else:
                st.error("❌ No users configured in USER_ROLES")
                st.warning("Configure user roles in the code before use")

# ------------------------
# Run Application
# ------------------------
if __name__ == "__main__":
    main()
