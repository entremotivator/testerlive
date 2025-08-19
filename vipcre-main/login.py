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
        st.markdown("**Access Control:**")
        st.success("✅ Administrators - Full Access")
        st.info("👤 Subscribers - Limited Access")
        st.error("❌ Customers - Access Denied")
        
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
    
    if user_role == 'administrator':
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
        tab1, tab2, tab3 = st.tabs(["Dashboard", "User Management", "Settings"])
        
        with tab1:
            st.write("📊 **Admin Dashboard**")
            st.info("Access to all system metrics and analytics")
            
        with tab2:
            st.write("👥 **User Management**")
            st.info("Manage user accounts and permissions")
            
        with tab3:
            st.write("⚙️ **System Settings**")
            st.info("Configure system-wide settings")
            
    elif user_role == 'subscriber':
        with col1:
            st.metric("Access Level", "Subscriber", "60%")
        with col2:
            st.metric("Permissions", "Limited", "⚠️")
        with col3:
            st.metric("Status", "Active", "🟢")
            
        st.markdown("---")
        st.info("📖 **Subscriber Access Granted**")
        st.write("You have access to subscriber-only content:")
        
        # Subscriber-specific features
        tab1, tab2 = st.tabs(["Content", "Profile"])
        
        with tab1:
            st.write("📚 **Subscriber Content**")
            st.success("Access to premium articles and resources")
            
        with tab2:
            st.write("👤 **Profile Settings**")
            st.success("Manage your subscription and preferences")

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
                
                with st.spinner("Authenticating..."):
                    try:
                        # Attempt to get token
                        token = auth.get_token(username_input, password_input)
                        
                        if token and auth.verify_token(token):
                            user_role = auth.get_user_role(token)
                            
                            # Check if user role is allowed
                            if user_role in ['subscriber', 'administrator']:
                                st.session_state['token'] = token
                                st.session_state['role'] = user_role
                                st.session_state['username'] = username_input
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
                        st.error(f"🔥 **Connection Error**: {str(e)}")
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
        
        **Customers are not permitted to access this system.**
        
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
            if st.button("🔓 Log Out", use_container_width=True):
                # Clear session state
                for key in ['token', 'role', 'username']:
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
            if ('token' in st.session_state and 
                'role' in st.session_state and 
                auth.verify_token(st.session_state['token'])):
                
                # User is authenticated - show main page
                username = st.session_state.get('username', 'User')
                main_page(st.session_state['role'], username)
                logout()
                
            else:
                # User not authenticated - show login page
                if 'token' in st.session_state:
                    # Clear invalid session
                    for key in ['token', 'role', 'username']:
                        if key in st.session_state:
                            del st.session_state[key]
                
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
            
            **Features:**
            - 🔐 Secure WordPress authentication
            - 👥 Role-based access control
            - 🚫 Customer access restriction
            - 📊 Admin and subscriber dashboards
            
            **Setup Instructions:**
            1. Enter your WordPress site URL in the sidebar
            2. Provide your API key for authentication
            3. Log in with your WordPress credentials
            
            **Access Levels:**
            - **Administrators**: Full system access
            - **Subscribers**: Content access
            - **Customers**: Access denied
            """)

# ------------------------
# Run Application
# ------------------------
if __name__ == "__main__":
    main()
