import streamlit as st
from wordpress_auth import WordpressAuth

# Set page configuration
st.set_page_config(
    page_title="VIP Credit Systems - Home",
    page_icon="💳",
    layout="wide"
)

# Check if user is authenticated (this would come from your main app logic)
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

def logout():
    """Handle user logout."""
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.token = None
    st.success("👋 Logged out successfully!")
    st.rerun()

def home_page():
    """Display the main home page for authenticated users."""
    # Sidebar with user info and logout
    with st.sidebar:
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.title("💳 VIP Credit")
        
        st.success(f"👤 Welcome, {st.session_state.user_role.title()}!")
        
        if st.button("🚪 Logout", use_container_width=True):
            logout()
        
        st.markdown("---")
        st.info("📌 Navigate using the menu above")

    # Main content area
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Main logo
        try:
            st.image("logooo.png", use_column_width=True)
        except:
            st.title("💳 VIP Credit Systems")

        st.title("VIP Credit Systems")
        st.subheader("Your Comprehensive Credit Management Solution")

        # Welcome message based on user role
        if st.session_state.user_role == 'administrator':
            st.info("🛠️ **Administrator Access** - You have full system privileges")
        elif st.session_state.user_role == 'subscriber':
            st.info("📊 **Subscriber Access** - Welcome to your credit dashboard")
        else:
            st.info(f"✅ **{st.session_state.user_role.title()} Access** - Welcome to VIP Credit Systems")

        # Introduction
        st.write("""
        Welcome to **VIP Credit Systems**, where managing your credit has never been easier. 
        Our system provides comprehensive tools and insights to help you understand and optimize your credit profile.
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

        # Additional Features Section
        with st.expander("⚡ Additional Features"):
            st.markdown("""
            - **Recent Transactions** - Track your latest financial activity
            - **Upcoming Payments** - Never miss a payment deadline
            - **New Credit Accounts** - Monitor recently opened accounts
            - **Export Data** - Download your financial reports
            """)

        # Call to action
        st.markdown("---")
        st.success("""
        🚀 **Ready to get started?** 
        
        Use the navigation menu above to explore your credit management tools and start optimizing your financial profile today!
        """)

# Main logic
if st.session_state.authenticated:
    home_page()
else:
    st.error("🔒 Please log in to access this page")
    st.markdown("[👆 Go to Login Page](Login)")
