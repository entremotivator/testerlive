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
                st.sidebar.error("🚫 **Access Denied**")
                st.sidebar.warning("""
                **Account upgrade required**
                
                Your account needs VIP access to use this system.
                
                [**Join VIP Program**](https://vipbusinesscredit.com/)
                """)
                return False
            
            # Allow access for all other roles
            st.session_state.authenticated = True
            st.session_state.user_role = user_role
            st.session_state.token = token
            st.sidebar.success(f"✅ Welcome, {user_role.title()}!")
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
    st.session_state.user_role = None
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
            
            # Sign up section
            st.markdown("---")
            st.markdown("**New User?**")
            st.markdown("[🌟 Join VIP Program](https://vipbusinesscredit.com/)")
            
            # Help section
            with st.expander("❓ Access Levels"):
                st.markdown("""
                **Allowed:**
                - ✅ Administrator
                - ✅ Subscriber  
                - ✅ Editor/Author
                
                **Requires Upgrade:**
                - ❌ Customer
                """)
                
        else:
            # User info and logout
            st.success(f"👤 {st.session_state.user_role.title()}")
            
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
            if st.session_state.user_role == 'administrator':
                st.info("🛠️ **Administrator Access** - Full system privileges")
            elif st.session_state.user_role == 'subscriber':
                st.info("📊 **Subscriber Access** - Credit dashboard enabled")
            else:
                st.info(f"✅ **{st.session_state.user_role.title()} Access** - Welcome!")

            # Introduction for authenticated users
            st.write("""
            Welcome to **VIP Credit Systems**! Your comprehensive credit management dashboard is ready. 
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

            # Trends and Forecasting Section
            with st.expander("📊 Trends & Forecasting"):
                st.markdown("""
                - **Credit Score Trend** - Historical score tracking and projections
                - **Monthly Spending Trend** - Analyze spending patterns over time
                - **Credit Score vs. Credit Utilization** - Correlation analysis
                - **Debt Repayment Schedule** - Strategic payoff timeline
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

            # Preview of features
            st.markdown("## 🎯 System Features Preview")
            
            col_feat1, col_feat2 = st.columns(2)
            
            with col_feat1:
                st.markdown("""
                ### 📊 Credit Monitoring
                - Real-time credit score tracking
                - Credit utilization monitoring
                - Payment history analysis
                - Credit report summaries
                """)
                
                st.markdown("""
                ### 🔧 Account Management
                - Credit inquiry tracking
                - Credit limit optimization
                - Debt-to-income calculations
                - Balance management tools
                """)
            
            with col_feat2:
                st.markdown("""
                ### 📈 Analytics & Insights
                - Account age analysis
                - Payment pattern tracking
                - Credit breakdown reports
                - Balance prioritization
                """)
                
                st.markdown("""
                ### 🛠️ Management Tools
                - Credit score simulation
                - Debt reduction planning
                - Improvement recommendations
                - Custom alert system
                """)

            # Sign up call to action
            st.markdown("---")
            st.info("""
            🌟 **New to VIP Credit Systems?** 
            
            [**Join our VIP Business Credit Program**](https://vipbusinesscredit.com/) to get full access to all credit management tools and expert guidance!
            """)

# Main application logic
sidebar_content()
main_content()
