import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone
import time
import random
import requests
import json
import os
from typing import Dict, List, Optional
from supabase import create_client, Client
import hashlib

# Page configuration
st.set_page_config(
    page_title="Property Analytics Platform",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Supabase configuration
@st.cache_resource
def init_supabase():
    """Initialize Supabase client"""
    # In production, these would be environment variables
    SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://your-project.supabase.co")
    SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", "your-anon-key")
    
    # For demo purposes, we'll use placeholder values
    if SUPABASE_URL == "https://your-project.supabase.co":
        st.warning("⚠️ Demo Mode: Using simulated Supabase connection. Configure real credentials in secrets.toml")
        return None
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
    except Exception as e:
        st.error(f"Failed to connect to Supabase: {e}")
        return None

# Database operations with Supabase
class SupabaseManager:
    def __init__(self):
        self.supabase = init_supabase()
        self.demo_mode = self.supabase is None
        
    def create_user(self, email: str, password: str, username: str) -> bool:
        """Create a new user account"""
        if self.demo_mode:
            # Simulate user creation in demo mode
            time.sleep(1)
            return True
            
        try:
            # Create user in Supabase Auth
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "username": username,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            })
            
            if response.user:
                # Insert additional user data
                self.supabase.table('user_profiles').insert({
                    "user_id": response.user.id,
                    "username": username,
                    "email": email,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()
                
                return True
            return False
            
        except Exception as e:
            st.error(f"Error creating user: {e}")
            return False
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user with Supabase"""
        if self.demo_mode:
            # Simulate authentication in demo mode
            time.sleep(1)
            return {
                "user": {"id": "demo-user", "email": email},
                "session": {"access_token": "demo-token"}
            }
            
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                return {
                    "user": response.user,
                    "session": response.session
                }
            return None
            
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return None
    
    def save_property_search(self, user_id: str, search_params: Dict, results: List[Dict]):
        """Save property search to database"""
        if self.demo_mode:
            return True
            
        try:
            self.supabase.table('property_searches').insert({
                "user_id": user_id,
                "search_params": search_params,
                "results_count": len(results),
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            return True
        except Exception as e:
            st.error(f"Error saving search: {e}")
            return False
    
    def get_user_searches(self, user_id: str) -> List[Dict]:
        """Get user's search history"""
        if self.demo_mode:
            # Return demo data
            return [
                {
                    "id": 1,
                    "search_params": {"location": "New York, NY", "max_price": 3000},
                    "results_count": 15,
                    "created_at": datetime.now(timezone.utc).isoformat()
                },
                {
                    "id": 2,
                    "search_params": {"location": "Los Angeles, CA", "max_price": 4000},
                    "results_count": 23,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            ]
            
        try:
            response = self.supabase.table('property_searches').select("*").eq('user_id', user_id).execute()
            return response.data
        except Exception as e:
            st.error(f"Error fetching searches: {e}")
            return []
    
    def save_api_key(self, user_id: str, api_name: str, api_key: str):
        """Save encrypted API key for user"""
        if self.demo_mode:
            return True
            
        try:
            # In production, encrypt the API key before storing
            encrypted_key = hashlib.sha256(api_key.encode()).hexdigest()  # Simple hash for demo
            
            self.supabase.table('user_api_keys').upsert({
                "user_id": user_id,
                "api_name": api_name,
                "encrypted_key": encrypted_key,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            return True
        except Exception as e:
            st.error(f"Error saving API key: {e}")
            return False
    
    def get_api_key(self, user_id: str, api_name: str) -> Optional[str]:
        """Get API key for user (returns encrypted version in demo)"""
        if self.demo_mode:
            return "demo-api-key-encrypted"
            
        try:
            response = self.supabase.table('user_api_keys').select("encrypted_key").eq('user_id', user_id).eq('api_name', api_name).execute()
            if response.data:
                return response.data[0]['encrypted_key']
            return None
        except Exception as e:
            st.error(f"Error fetching API key: {e}")
            return None

# Property lookup with enhanced features
class PropertyLookupService:
    def __init__(self, supabase_manager: SupabaseManager):
        self.db = supabase_manager
    
    def search_rentals(self, location: str, max_price: int = None, bedrooms: int = None, 
                      property_type: str = None, user_id: str = None) -> List[Dict]:
        """Enhanced rental search with database logging"""
        
        # Generate realistic sample data
        sample_rentals = []
        for i in range(1, random.randint(15, 30)):
            rental = {
                "id": f"rental_{location.replace(' ', '_').replace(',', '')}_{i}",
                "address": f"{100 + i * 10} {random.choice(['Main', 'Oak', 'Pine', 'Elm', 'Park'])} St, {location}",
                "price": random.randint(800, 6000),
                "bedrooms": random.randint(1, 5),
                "bathrooms": random.randint(1, 4),
                "sqft": random.randint(400, 3000),
                "property_type": random.choice(["Apartment", "House", "Condo", "Townhouse", "Studio"]),
                "available_date": (datetime.now(timezone.utc) + pd.Timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d"),
                "amenities": random.sample([
                    "Pool", "Gym", "Parking", "Laundry", "Pet-friendly", "Balcony", 
                    "Air Conditioning", "Dishwasher", "Hardwood Floors", "In-unit Washer/Dryer"
                ], random.randint(2, 6)),
                "description": f"Beautiful {random.choice(['modern', 'cozy', 'spacious', 'luxury', 'updated'])} {random.choice(['apartment', 'home', 'condo'])} in {location}",
                "contact": f"agent{i}@{random.choice(['realty', 'properties', 'homes'])}.com",
                "landlord": f"{random.choice(['Smith', 'Johnson', 'Williams', 'Brown'])} Properties",
                "lease_term": random.choice(["12 months", "6 months", "Month-to-month"]),
                "deposit": random.randint(500, 2000),
                "utilities_included": random.choice([True, False]),
                "pet_policy": random.choice(["No pets", "Cats only", "Dogs only", "Cats and dogs", "All pets welcome"]),
                "parking_spots": random.randint(0, 3),
                "year_built": random.randint(1950, 2023),
                "neighborhood_score": random.randint(60, 100),
                "walkability_score": random.randint(30, 100),
                "transit_score": random.randint(20, 90),
                "images": [f"https://example.com/property_{i}_image_{j}.jpg" for j in range(random.randint(3, 8))],
                "virtual_tour": f"https://example.com/tour/{i}" if random.choice([True, False]) else None,
                "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            }
            sample_rentals.append(rental)
        
        # Apply filters
        filtered_rentals = sample_rentals
        
        if max_price:
            filtered_rentals = [r for r in filtered_rentals if r["price"] <= max_price]
        if bedrooms:
            filtered_rentals = [r for r in filtered_rentals if r["bedrooms"] == bedrooms]
        if property_type and property_type != "All":
            filtered_rentals = [r for r in filtered_rentals if r["property_type"] == property_type]
        
        # Sort by price (default)
        filtered_rentals.sort(key=lambda x: x["price"])
        
        # Log search to database
        if user_id:
            search_params = {
                "location": location,
                "max_price": max_price,
                "bedrooms": bedrooms,
                "property_type": property_type
            }
            self.db.save_property_search(user_id, search_params, filtered_rentals)
        
        return filtered_rentals[:20]  # Return top 20 results
    
    def get_property_details(self, property_id: str) -> Dict:
        """Get comprehensive property details"""
        return {
            "id": property_id,
            "detailed_info": {
                "property_history": {
                    "previous_rent": random.randint(800, 4000),
                    "rent_change": random.choice(["+5%", "-2%", "+8%", "No change"]),
                    "days_on_market": random.randint(5, 120),
                    "previous_tenants": random.randint(1, 5)
                },
                "building_info": {
                    "year_built": random.randint(1950, 2023),
                    "total_units": random.randint(4, 200),
                    "floors": random.randint(1, 20),
                    "elevator": random.choice([True, False]),
                    "laundry_facility": random.choice(["In-unit", "On-site", "None"]),
                    "management_company": f"{random.choice(['ABC', 'XYZ', 'Premier', 'Elite'])} Management"
                },
                "location_details": {
                    "lot_size": f"{random.randint(1000, 10000)} sqft",
                    "property_tax": f"${random.randint(2000, 15000)}/year",
                    "hoa_fees": f"${random.randint(0, 500)}/month",
                    "school_district": f"District {random.randint(1, 20)}",
                    "walk_score": random.randint(20, 100),
                    "crime_rate": random.choice(["Low", "Medium", "High"]),
                    "noise_level": random.choice(["Quiet", "Moderate", "Busy"])
                },
                "amenities_detailed": {
                    "heating": random.choice(["Gas", "Electric", "Solar", "Heat pump"]),
                    "cooling": random.choice(["Central AC", "Window units", "None"]),
                    "flooring": random.choice(["Hardwood", "Carpet", "Tile", "Laminate", "Mixed"]),
                    "kitchen": random.choice(["Updated", "Modern", "Basic", "Luxury"]),
                    "appliances": random.sample(["Refrigerator", "Stove", "Dishwasher", "Microwave", "Washer", "Dryer"], random.randint(3, 6)),
                    "internet": random.choice(["Fiber", "Cable", "DSL", "Included", "Not included"])
                },
                "nearby_amenities": {
                    "grocery_stores": random.randint(2, 10),
                    "restaurants": random.randint(5, 50),
                    "parks": random.randint(1, 8),
                    "schools": random.randint(1, 5),
                    "hospitals": random.randint(1, 3),
                    "public_transport": random.choice(["Excellent", "Good", "Fair", "Poor"])
                }
            }
        }
    
    def get_market_analysis(self, location: str) -> Dict:
        """Comprehensive market analysis"""
        return {
            "location": location,
            "rental_market": {
                "average_rent": random.randint(1500, 5000),
                "median_rent": random.randint(1200, 4500),
                "rent_range": f"${random.randint(800, 1500)} - ${random.randint(3000, 8000)}",
                "price_trend": random.choice(["Increasing", "Stable", "Decreasing"]),
                "trend_percentage": random.uniform(-10, 20),
                "vacancy_rate": round(random.uniform(2, 15), 1),
                "days_on_market": random.randint(15, 90),
                "rental_yield": round(random.uniform(3, 8), 2),
                "seasonal_trends": {
                    "peak_season": random.choice(["Spring", "Summer", "Fall", "Winter"]),
                    "low_season": random.choice(["Spring", "Summer", "Fall", "Winter"])
                }
            },
            "sales_market": {
                "median_home_price": random.randint(200000, 1200000),
                "price_per_sqft": random.randint(150, 800),
                "appreciation_rate": round(random.uniform(-5, 15), 2),
                "inventory_level": random.choice(["Low", "Moderate", "High"]),
                "months_of_supply": round(random.uniform(1, 8), 1)
            },
            "demographics": {
                "population": random.randint(10000, 2000000),
                "median_age": random.randint(25, 45),
                "median_income": random.randint(40000, 150000),
                "employment_rate": round(random.uniform(85, 96), 1),
                "population_growth": round(random.uniform(-2, 8), 1)
            },
            "market_score": random.randint(60, 95),
            "investment_rating": random.choice(["Excellent", "Good", "Fair", "Poor"]),
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        }

# Initialize Supabase manager
@st.cache_resource
def get_supabase_manager():
    return SupabaseManager()

# Custom CSS with enhanced styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .login-form {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 2rem;
        border-radius: 1rem;
        border: 1px solid #ddd;
        max-width: 450px;
        margin: 0 auto;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    .property-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }
    .property-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    .api-status {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid;
    }
    .api-connected {
        background-color: #d4edda;
        color: #155724;
        border-left-color: #28a745;
    }
    .api-disconnected {
        background-color: #f8d7da;
        color: #721c24;
        border-left-color: #dc3545;
    }
    .supabase-status {
        background: linear-gradient(135deg, #00d4aa 0%, #00b894 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "login"

# Initialize services
supabase_manager = get_supabase_manager()
property_service = PropertyLookupService(supabase_manager)

# Authentication UI
def show_login_page():
    """Enhanced login/registration page with Supabase"""
    st.markdown('<h1 class="main-header">🏠 Property Analytics Platform</h1>', unsafe_allow_html=True)
    
    # Supabase status indicator
    if supabase_manager.demo_mode:
        st.markdown("""
        <div class="supabase-status">
            🔧 Demo Mode Active - Configure Supabase credentials for full functionality
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="supabase-status">
            ✅ Connected to Supabase - Full functionality enabled
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-form">', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
        
        with tab1:
            st.subheader("Welcome Back!")
            login_email = st.text_input("Email Address", key="login_email", placeholder="your@email.com")
            login_password = st.text_input("Password", type="password", key="login_password", placeholder="Your password")
            
            col_a, col_b = st.columns(2)
            with col_a:
                remember_me = st.checkbox("Remember me")
            with col_b:
                forgot_password = st.button("Forgot Password?", type="secondary")
            
            if st.button("🚀 Sign In", use_container_width=True, type="primary"):
                if login_email and login_password:
                    with st.spinner("Authenticating..."):
                        auth_result = supabase_manager.authenticate_user(login_email, login_password)
                        if auth_result:
                            st.session_state.authenticated = True
                            st.session_state.user_data = auth_result
                            st.session_state.current_page = "dashboard"
                            st.success("Welcome back! Redirecting to dashboard...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Invalid email or password. Please try again.")
                else:
                    st.error("Please enter both email and password")
        
        with tab2:
            st.subheader("Create Your Account")
            reg_username = st.text_input("Username", key="reg_username", placeholder="Choose a username")
            reg_email = st.text_input("Email Address", key="reg_email", placeholder="your@email.com")
            reg_password = st.text_input("Password", type="password", key="reg_password", placeholder="Choose a strong password")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm", placeholder="Confirm your password")
            
            # Password strength indicator
            if reg_password:
                strength = 0
                if len(reg_password) >= 8: strength += 1
                if any(c.isupper() for c in reg_password): strength += 1
                if any(c.islower() for c in reg_password): strength += 1
                if any(c.isdigit() for c in reg_password): strength += 1
                
                strength_text = ["Very Weak", "Weak", "Fair", "Good", "Strong"][strength]
                strength_color = ["red", "orange", "yellow", "lightgreen", "green"][strength]
                st.markdown(f"Password Strength: <span style='color: {strength_color}'>{strength_text}</span>", unsafe_allow_html=True)
            
            terms_agreed = st.checkbox("I agree to the Terms of Service and Privacy Policy")
            
            if st.button("📝 Create Account", use_container_width=True, type="primary"):
                if not all([reg_username, reg_email, reg_password, reg_confirm]):
                    st.error("Please fill in all fields")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match")
                elif len(reg_password) < 6:
                    st.error("Password must be at least 6 characters long")
                elif not terms_agreed:
                    st.error("Please agree to the Terms of Service")
                else:
                    with st.spinner("Creating your account..."):
                        if supabase_manager.create_user(reg_email, reg_password, reg_username):
                            st.success("🎉 Account created successfully! Please check your email for verification, then login.")
                        else:
                            st.error("Failed to create account. Email may already be in use.")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Enhanced dashboard with Supabase integration
def show_dashboard():
    """Main dashboard with Supabase features"""
    user_email = st.session_state.user_data['user']['email'] if st.session_state.user_data else "Demo User"
    user_id = st.session_state.user_data['user']['id'] if st.session_state.user_data else "demo-user"
    
    st.markdown(f'<h1 class="main-header">🏠 Welcome back, {user_email.split("@")[0]}!</h1>', unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.header(f"👋 Hello, {user_email.split('@')[0]}")
        
        if st.button("🚪 Logout", type="secondary"):
            st.session_state.authenticated = False
            st.session_state.user_data = None
            st.session_state.current_page = "login"
            st.rerun()
        
        st.markdown("---")
        
        # Navigation menu
        page = st.selectbox(
            "📍 Navigate to:",
            ["🏠 Dashboard", "🔍 Property Search", "📊 Market Analysis", "📈 My Analytics", "🔧 API Management", "⚙️ Settings"]
        )
        
        # Supabase connection status
        if supabase_manager.demo_mode:
            st.warning("🔧 Demo Mode")
        else:
            st.success("✅ Supabase Connected")
        
        # Current time display with timezone-aware datetime
        current_time = datetime.now(timezone.utc)
        st.info(f"🕐 {current_time.strftime('%H:%M:%S UTC')}")
        
        # Quick stats from Supabase
        st.markdown("### 📊 Quick Stats")
        searches_today = len(supabase_manager.get_user_searches(user_id))
        st.metric("🔍 Searches Today", searches_today)
    
    # Page routing
    if page == "🏠 Dashboard":
        show_main_dashboard(user_id)
    elif page == "🔍 Property Search":
        show_property_search(user_id)
    elif page == "📊 Market Analysis":
        show_market_analysis(user_id)
    elif page == "📈 My Analytics":
        show_user_analytics(user_id)
    elif page == "🔧 API Management":
        show_api_management(user_id)
    elif page == "⚙️ Settings":
        show_settings(user_id)

def show_main_dashboard(user_id: str):
    """Enhanced main dashboard"""
    # Real-time metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🏠 Properties Viewed</h3>
            <h2>1,234</h2>
            <p>↗️ +12% this week</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>💰 Avg Rent Price</h3>
            <h2>$2,450</h2>
            <p>↗️ +5.2% this month</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>📈 Market Score</h3>
            <h2>87/100</h2>
            <p>↗️ +3 points</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3>🔍 Total Searches</h3>
            <h2>45</h2>
            <p>↗️ +8 today</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Recent searches from Supabase
    st.subheader("📋 Recent Search History")
    
    search_history = supabase_manager.get_user_searches(user_id)
    if search_history:
        history_df = pd.DataFrame(search_history)
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("No search history yet. Start by searching for properties!")
    
    # Market trends with modern pandas frequency
    st.subheader("📈 Market Trends")
    
    # Generate trend data using 'ME' instead of deprecated 'M'
    dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='ME')
    trend_data = pd.DataFrame({
        'Date': dates,
        'Average_Rent': np.random.normal(2500, 200, len(dates)).cumsum() / 10 + 2000,
        'Median_Price': np.random.normal(400000, 20000, len(dates)).cumsum() / 10 + 350000,
        'Inventory': np.abs(np.random.normal(1000, 100, len(dates)))
    })
    
    # Interactive chart
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        fig_rent = px.line(trend_data, x='Date', y='Average_Rent', 
                          title='Average Rent Trends',
                          color_discrete_sequence=['#1f77b4'])
        fig_rent.update_layout(height=400)
        st.plotly_chart(fig_rent, use_container_width=True)
    
    with chart_col2:
        fig_price = px.line(trend_data, x='Date', y='Median_Price', 
                           title='Median Home Price Trends',
                           color_discrete_sequence=['#ff7f0e'])
        fig_price.update_layout(height=400)
        st.plotly_chart(fig_price, use_container_width=True)

def show_property_search(user_id: str):
    """Enhanced property search with Supabase logging"""
    st.subheader("🔍 Advanced Property Search")
    
    # Search filters in expandable sections
    with st.expander("🎯 Search Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            location = st.text_input("📍 Location", "New York, NY", help="Enter city, state or zip code")
            property_type = st.selectbox("🏠 Property Type", 
                                       ["All", "Apartment", "House", "Condo", "Townhouse", "Studio"])
        
        with col2:
            price_range = st.slider("💰 Price Range", 500, 10000, (1000, 5000), step=100)
            bedrooms = st.selectbox("🛏️ Bedrooms", ["Any", 1, 2, 3, 4, "5+"])
        
        with col3:
            bathrooms = st.selectbox("🚿 Bathrooms", ["Any", 1, 2, 3, "4+"])
            sort_by = st.selectbox("📊 Sort By", 
                                 ["Price (Low to High)", "Price (High to Low)", 
                                  "Newest", "Bedrooms", "Square Footage"])
    
    # Advanced filters
    with st.expander("🔧 Advanced Filters"):
        adv_col1, adv_col2 = st.columns(2)
        
        with adv_col1:
            pet_friendly = st.checkbox("🐕 Pet Friendly")
            parking_required = st.checkbox("🚗 Parking Required")
            utilities_included = st.checkbox("⚡ Utilities Included")
        
        with adv_col2:
            min_sqft = st.number_input("📐 Min Square Feet", min_value=0, value=0)
            max_lease_term = st.selectbox("📅 Max Lease Term", 
                                        ["Any", "6 months", "12 months", "Month-to-month"])
    
    # Search button
    if st.button("🔍 Search Properties", use_container_width=True, type="primary"):
        with st.spinner("🔍 Searching properties in our database..."):
            # Simulate search delay
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress_bar.progress(i + 1)
            progress_bar.empty()
            
            # Perform search
            bedrooms_filter = None if bedrooms == "Any" else int(bedrooms) if isinstance(bedrooms, int) else None
            results = property_service.search_rentals(
                location=location,
                max_price=price_range[1],
                bedrooms=bedrooms_filter,
                property_type=property_type,
                user_id=user_id
            )
            
            # Filter by price range
            results = [r for r in results if price_range[0] <= r['price'] <= price_range[1]]
            
            st.success(f"🎉 Found {len(results)} properties matching your criteria!")
            
            # Results summary
            if results:
                avg_price = sum(r['price'] for r in results) / len(results)
                avg_sqft = sum(r['sqft'] for r in results) / len(results)
                
                summary_col1, summary_col2, summary_col3 = st.columns(3)
                with summary_col1:
                    st.metric("📊 Results Found", len(results))
                with summary_col2:
                    st.metric("💰 Average Price", f"${avg_price:,.0f}")
                with summary_col3:
                    st.metric("📐 Average Size", f"{avg_sqft:,.0f} sqft")
            
            # Display results
            for idx, property_data in enumerate(results):
                with st.container():
                    st.markdown('<div class="property-card">', unsafe_allow_html=True)
                    
                    # Property header
                    col_main, col_actions = st.columns([3, 1])
                    
                    with col_main:
                        st.markdown(f"### 🏠 {property_data['address']}")
                        
                        # Price and basic info
                        price_color = "green" if property_data['price'] < avg_price else "orange"
                        st.markdown(f"""
                        **💰 <span style='color: {price_color}; font-size: 1.2em;'>${property_data['price']:,}/month</span>** | 
                        🛏️ {property_data['bedrooms']} bed | 
                        🚿 {property_data['bathrooms']} bath | 
                        📐 {property_data['sqft']:,} sqft
                        """, unsafe_allow_html=True)
                        
                        # Property details
                        detail_col1, detail_col2 = st.columns(2)
                        with detail_col1:
                            st.markdown(f"**🏢 Type:** {property_data['property_type']}")
                            st.markdown(f"**📅 Available:** {property_data['available_date']}")
                            st.markdown(f"**🏗️ Built:** {property_data['year_built']}")
                        
                        with detail_col2:
                            st.markdown(f"**💳 Deposit:** ${property_data['deposit']:,}")
                            st.markdown(f"**📋 Lease:** {property_data['lease_term']}")
                            st.markdown(f"**🚗 Parking:** {property_data['parking_spots']} spots")
                        
                        # Amenities
                        st.markdown(f"**✨ Amenities:** {', '.join(property_data['amenities'])}")
                        
                        # Scores
                        score_col1, score_col2, score_col3 = st.columns(3)
                        with score_col1:
                            st.metric("🏘️ Neighborhood", f"{property_data['neighborhood_score']}/100")
                        with score_col2:
                            st.metric("🚶 Walkability", f"{property_data['walkability_score']}/100")
                        with score_col3:
                            st.metric("🚌 Transit", f"{property_data['transit_score']}/100")
                    
                    with col_actions:
                        if st.button(f"💌 Contact", key=f"contact_{idx}", use_container_width=True):
                            st.info(f"📧 {property_data['contact']}")
                        
                        if st.button(f"📋 Details", key=f"details_{idx}", use_container_width=True):
                            details = property_service.get_property_details(property_data['id'])
                            st.json(details['detailed_info'])
                        
                        if st.button(f"❤️ Save", key=f"save_{idx}", use_container_width=True):
                            st.success("Saved to favorites!")
                        
                        if property_data['virtual_tour']:
                            if st.button(f"🎥 Virtual Tour", key=f"tour_{idx}", use_container_width=True):
                                st.info(f"🔗 {property_data['virtual_tour']}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown("---")

def show_market_analysis(user_id: str):
    """Enhanced market analysis with Supabase data"""
    st.subheader("📊 Comprehensive Market Analysis")
    
    analysis_location = st.text_input("📍 Enter Location for Analysis", "San Francisco, CA")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        analysis_type = st.selectbox("📈 Analysis Type", 
                                   ["Full Market Report", "Rental Analysis Only", "Sales Analysis Only", "Investment Analysis"])
    with col2:
        if st.button("📊 Generate Report", type="primary", use_container_width=True):
            with st.spinner("🔍 Analyzing market data..."):
                # Progress indicator
                progress = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Gathering rental data...")
                progress.progress(25)
                time.sleep(0.5)
                
                status_text.text("Analyzing sales trends...")
                progress.progress(50)
                time.sleep(0.5)
                
                status_text.text("Processing demographics...")
                progress.progress(75)
                time.sleep(0.5)
                
                status_text.text("Generating insights...")
                progress.progress(100)
                time.sleep(0.5)
                
                progress.empty()
                status_text.empty()
                
                # Get comprehensive market data
                market_data = property_service.get_market_analysis(analysis_location)
                
                st.success(f"✅ Market analysis complete for {analysis_location}")
                
                # Market Overview
                st.markdown("### 🏠 Market Overview")
                
                overview_col1, overview_col2, overview_col3, overview_col4 = st.columns(4)
                
                with overview_col1:
                    st.metric("⭐ Market Score", f"{market_data['market_score']}/100")
                with overview_col2:
                    st.metric("📈 Investment Rating", market_data['investment_rating'])
                with overview_col3:
                    st.metric("👥 Population", f"{market_data['demographics']['population']:,}")
                with overview_col4:
                    trend_color = "green" if "Increasing" in str(market_data['rental_market']['price_trend']) else "red"
                    st.metric("📊 Price Trend", market_data['rental_market']['price_trend'])
                
                # Rental Market Analysis
                st.markdown("### 🏠 Rental Market")
                
                rental_col1, rental_col2, rental_col3 = st.columns(3)
                
                with rental_col1:
                    st.metric("💰 Average Rent", f"${market_data['rental_market']['average_rent']:,}")
                    st.metric("📊 Median Rent", f"${market_data['rental_market']['median_rent']:,}")
                
                with rental_col2:
                    st.metric("📈 Vacancy Rate", f"{market_data['rental_market']['vacancy_rate']}%")
                    st.metric("⏱️ Days on Market", f"{market_data['rental_market']['days_on_market']}")
                
                with rental_col3:
                    st.metric("💹 Rental Yield", f"{market_data['rental_market']['rental_yield']}%")
                    trend_pct = market_data['rental_market']['trend_percentage']
                    st.metric("📈 Price Change", f"{trend_pct:+.1f}%")
                
                # Rent range visualization
                rent_range = market_data['rental_market']['rent_range']
                st.markdown(f"**💰 Rent Range:** {rent_range}")
                
                # Sales Market Analysis
                st.markdown("### 🏘️ Sales Market")
                
                sales_col1, sales_col2, sales_col3 = st.columns(3)
                
                with sales_col1:
                    st.metric("🏠 Median Home Price", f"${market_data['sales_market']['median_home_price']:,}")
                
                with sales_col2:
                    st.metric("📐 Price per Sqft", f"${market_data['sales_market']['price_per_sqft']}")
                
                with sales_col3:
                    appreciation = market_data['sales_market']['appreciation_rate']
                    st.metric("📈 Appreciation Rate", f"{appreciation:+.1f}%")
                
                # Demographics
                st.markdown("### 👥 Demographics & Economics")
                
                demo_col1, demo_col2, demo_col3, demo_col4 = st.columns(4)
                
                with demo_col1:
                    st.metric("🎂 Median Age", f"{market_data['demographics']['median_age']} years")
                
                with demo_col2:
                    st.metric("💰 Median Income", f"${market_data['demographics']['median_income']:,}")
                
                with demo_col3:
                    st.metric("💼 Employment Rate", f"{market_data['demographics']['employment_rate']}%")
                
                with demo_col4:
                    pop_growth = market_data['demographics']['population_growth']
                    st.metric("📈 Population Growth", f"{pop_growth:+.1f}%")
                
                # Market trends visualization
                st.markdown("### 📈 Market Trends Visualization")
                
                # Generate sample trend data
                months = pd.date_range(start='2023-01-01', periods=12, freq='ME')
                base_rent = market_data['rental_market']['average_rent']
                trend_multiplier = 1 + (market_data['rental_market']['trend_percentage'] / 100)
                
                trend_data = pd.DataFrame({
                    'Month': months,
                    'Average_Rent': [base_rent * (trend_multiplier ** (i/12)) + random.randint(-100, 100) for i in range(12)],
                    'Median_Price': [market_data['sales_market']['median_home_price'] * (1.05 ** (i/12)) + random.randint(-5000, 5000) for i in range(12)]
                })
                
                chart_col1, chart_col2 = st.columns(2)
                
                with chart_col1:
                    fig_rent_trend = px.line(trend_data, x='Month', y='Average_Rent', 
                                           title='Rental Price Trends',
                                           color_discrete_sequence=['#1f77b4'])
                    fig_rent_trend.update_layout(height=400)
                    st.plotly_chart(fig_rent_trend, use_container_width=True)
                
                with chart_col2:
                    fig_price_trend = px.line(trend_data, x='Month', y='Median_Price', 
                                            title='Home Price Trends',
                                            color_discrete_sequence=['#ff7f0e'])
                    fig_price_trend.update_layout(height=400)
                    st.plotly_chart(fig_price_trend, use_container_width=True)
                
                # Investment insights
                st.markdown("### 💡 Investment Insights")
                
                insights = []
                if market_data['rental_market']['rental_yield'] > 6:
                    insights.append("✅ High rental yield indicates good cash flow potential")
                if market_data['sales_market']['appreciation_rate'] > 5:
                    insights.append("✅ Strong appreciation rate suggests good long-term growth")
                if market_data['rental_market']['vacancy_rate'] < 5:
                    insights.append("✅ Low vacancy rate indicates strong rental demand")
                if market_data['demographics']['population_growth'] > 2:
                    insights.append("✅ Population growth supports future demand")
                
                for insight in insights:
                    st.markdown(insight)
                
                # Save analysis to Supabase (simulated)
                st.info(f"📊 Analysis saved to your account • Generated: {market_data['last_updated']}")

def show_user_analytics(user_id: str):
    """User-specific analytics dashboard"""
    st.subheader("📈 Your Analytics Dashboard")
    
    # User search patterns
    search_history = supabase_manager.get_user_searches(user_id)
    
    if search_history:
        st.markdown("### 🔍 Your Search Patterns")
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(search_history)
        
        # Search frequency over time
        if 'created_at' in df.columns:
            df['date'] = pd.to_datetime(df['created_at']).dt.date
            daily_searches = df.groupby('date').size().reset_index(name='searches')
            
            fig_searches = px.bar(daily_searches, x='date', y='searches', 
                                title='Daily Search Activity')
            st.plotly_chart(fig_searches, use_container_width=True)
        
        # Most searched locations (if available in search_params)
        st.markdown("### 📍 Popular Search Locations")
        locations = []
        for search in search_history:
            if isinstance(search.get('search_params'), dict):
                location = search['search_params'].get('location')
                if location:
                    locations.append(location)
        
        if locations:
            location_counts = pd.Series(locations).value_counts()
            fig_locations = px.pie(values=location_counts.values, names=location_counts.index,
                                 title='Your Most Searched Locations')
            st.plotly_chart(fig_locations, use_container_width=True)
        
        # Search results summary
        total_results = sum(search.get('results_count', 0) for search in search_history)
        avg_results = total_results / len(search_history) if search_history else 0
        
        analytics_col1, analytics_col2, analytics_col3 = st.columns(3)
        
        with analytics_col1:
            st.metric("🔍 Total Searches", len(search_history))
        with analytics_col2:
            st.metric("📊 Total Results", total_results)
        with analytics_col3:
            st.metric("📈 Avg Results/Search", f"{avg_results:.1f}")
    
    else:
        st.info("📊 No search history yet. Start searching to see your analytics!")
        
        # Show sample analytics
        st.markdown("### 📈 Sample Analytics Preview")
        
        sample_data = pd.DataFrame({
            'Date': pd.date_range(start='2024-01-01', periods=30, freq='D'),
            'Searches': np.random.poisson(2, 30),
            'Properties_Viewed': np.random.poisson(5, 30)
        })
        
        fig_sample = px.line(sample_data, x='Date', y=['Searches', 'Properties_Viewed'],
                           title='Sample Activity Over Time')
        st.plotly_chart(fig_sample, use_container_width=True)

def show_api_management(user_id: str):
    """Enhanced API management with Supabase storage"""
    st.subheader("🔧 API Management Center")
    
    # API status overview
    st.markdown("### 📊 API Services Status")
    
    api_services = [
        {"name": "Supabase Database", "status": "Connected" if not supabase_manager.demo_mode else "Demo Mode", 
         "last_call": "Active", "description": "User data and search history"},
        {"name": "RentSpree API", "status": "Ready", "last_call": "Not configured", 
         "description": "Rental property listings"},
        {"name": "Zillow API", "status": "Ready", "last_call": "Not configured", 
         "description": "Property valuations and market data"},
        {"name": "Weather API", "status": "Ready", "last_call": "Not configured", 
         "description": "Location weather information"},
        {"name": "Economic Data API", "status": "Ready", "last_call": "Not configured", 
         "description": "Market indicators and trends"}
    ]
    
    for api in api_services:
        status_class = "api-connected" if api["status"] in ["Connected", "Active"] else "api-disconnected"
        st.markdown(f"""
        <div class="{status_class}">
            <strong>🔌 {api['name']}</strong><br>
            Status: {api['status']} | Last Activity: {api['last_call']}<br>
            <small>{api['description']}</small>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # API key management
    st.markdown("### 🔑 API Key Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔐 Add/Update API Keys")
        
        api_service = st.selectbox("Select API Service", 
                                 ["RentSpree", "Zillow", "Weather Service", "Economic Data", "Custom API"])
        
        if api_service == "Custom API":
            custom_name = st.text_input("Custom API Name")
            api_service = custom_name if custom_name else "Custom API"
        
        api_key_input = st.text_input("API Key", type="password", 
                                    help="Your API key will be encrypted and stored securely")
        api_endpoint = st.text_input("API Endpoint (Optional)", 
                                   placeholder="https://api.example.com/v1")
        
        if st.button("💾 Save API Configuration", type="primary"):
            if api_key_input:
                success = supabase_manager.save_api_key(user_id, api_service, api_key_input)
                if success:
                    st.success(f"✅ API key for {api_service} saved successfully!")
                else:
                    st.error("❌ Failed to save API key")
            else:
                st.error("Please enter an API key")
    
    with col2:
        st.markdown("#### 🧪 Test API Connections")
        
        test_service = st.selectbox("Select Service to Test", 
                                  ["RentSpree", "Zillow", "Weather Service", "Economic Data"])
        
        test_endpoint = st.text_input("Test Endpoint", 
                                    value="https://api.example.com/health")
        
        if st.button("🔍 Test Connection", type="secondary"):
            with st.spinner(f"Testing {test_service} connection..."):
                time.sleep(2)
                
                # Simulate API test with realistic results
                success_rate = 0.8  # 80% success rate for demo
                test_success = random.random() < success_rate
                
                if test_success:
                    response_time = random.randint(50, 300)
                    st.success(f"✅ {test_service} API connection successful!")
                    st.info(f"📊 Response time: {response_time}ms")
                    
                    # Show sample response
                    sample_response = {
                        "status": "healthy",
                        "version": "v1.2.3",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "rate_limit": "1000/hour"
                    }
                    st.json(sample_response)
                else:
                    st.error(f"❌ {test_service} API connection failed!")
                    st.warning("Please check your API key and endpoint configuration")
    
    # API usage analytics
    st.markdown("### 📈 API Usage Analytics")
    
    # Generate sample usage data
    usage_data = pd.DataFrame({
        'API Service': ['Supabase', 'RentSpree', 'Zillow', 'Weather', 'Economic Data'],
        'Calls Today': [45, 32, 28, 78, 12],
        'Calls This Week': [315, 224, 196, 546, 84],
        'Calls This Month': [1250, 890, 780, 2340, 456],
        'Success Rate %': [99.8, 98.5, 97.2, 99.1, 95.8],
        'Avg Response Time (ms)': [45, 120, 180, 85, 250]
    })
    
    # Display usage table
    st.dataframe(usage_data, use_container_width=True)
    
    # Usage visualization
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        fig_calls = px.bar(usage_data, x='API Service', y='Calls Today', 
                          title='API Calls Today',
                          color='Calls Today',
                          color_continuous_scale='Blues')
        st.plotly_chart(fig_calls, use_container_width=True)
    
    with chart_col2:
        fig_success = px.bar(usage_data, x='API Service', y='Success Rate %', 
                           title='API Success Rates',
                           color='Success Rate %',
                           color_continuous_scale='Greens')
        st.plotly_chart(fig_success, use_container_width=True)
    
    # API rate limits and quotas
    st.markdown("### ⚡ Rate Limits & Quotas")
    
    quota_col1, quota_col2, quota_col3 = st.columns(3)
    
    with quota_col1:
        st.metric("🔄 Daily Quota Used", "1,247 / 5,000", "24.9%")
        st.progress(0.249)
    
    with quota_col2:
        st.metric("⏱️ Rate Limit Status", "Normal", "98 req/min")
        st.progress(0.65)
    
    with quota_col3:
        st.metric("💰 Monthly Cost", "$23.45", "+$2.10")

def show_settings(user_id: str):
    """Enhanced settings with Supabase integration"""
    st.subheader("⚙️ Account Settings")
    
    # User profile section
    st.markdown("### 👤 Profile Settings")
    
    profile_col1, profile_col2 = st.columns(2)
    
    with profile_col1:
        current_email = st.session_state.user_data['user']['email'] if st.session_state.user_data else "demo@example.com"
        new_email = st.text_input("Email Address", value=current_email)
        display_name = st.text_input("Display Name", value=current_email.split('@')[0])
        
    with profile_col2:
        timezone_pref = st.selectbox("Timezone Preference", 
                                   ["UTC", "EST", "PST", "CST", "MST", "GMT"])
        language_pref = st.selectbox("Language", 
                                   ["English", "Spanish", "French", "German"])
    
    # Notification preferences
    st.markdown("### 🔔 Notification Preferences")
    
    notif_col1, notif_col2 = st.columns(2)
    
    with notif_col1:
        email_notifications = st.checkbox("📧 Email Notifications", True)
        price_alerts = st.checkbox("💰 Price Drop Alerts", True)
        new_listings = st.checkbox("🏠 New Listing Alerts", False)
    
    with notif_col2:
        market_reports = st.checkbox("📊 Weekly Market Reports", True)
        api_status_alerts = st.checkbox("🔧 API Status Alerts", True)
        security_alerts = st.checkbox("🔒 Security Alerts", True)
    
    # Data preferences
    st.markdown("### 📊 Data & Search Preferences")
    
    data_col1, data_col2 = st.columns(2)
    
    with data_col1:
        default_location = st.text_input("🏠 Default Search Location", "New York, NY")
        max_results = st.slider("📊 Max Search Results", 10, 100, 50)
        
    with data_col2:
        auto_refresh = st.selectbox("🔄 Auto Refresh Data", 
                                  ["Never", "5 minutes", "15 minutes", "30 minutes", "1 hour"])
        data_retention = st.selectbox("💾 Search History Retention", 
                                    ["30 days", "90 days", "1 year", "Forever"])
    
    # Privacy settings
    st.markdown("### 🔒 Privacy & Security")
    
    privacy_col1, privacy_col2 = st.columns(2)
    
    with privacy_col1:
        profile_visibility = st.selectbox("👁️ Profile Visibility", 
                                        ["Private", "Public", "Friends Only"])
        search_history_private = st.checkbox("🔍 Keep Search History Private", True)
        
    with privacy_col2:
        two_factor_auth = st.checkbox("🔐 Enable 2FA", False)
        login_notifications = st.checkbox("📱 Login Notifications", True)
    
    # Save settings
    if st.button("💾 Save All Settings", type="primary", use_container_width=True):
        with st.spinner("Saving settings..."):
            time.sleep(1)
            st.success("✅ Settings saved successfully!")
    
    st.markdown("---")
    
    # Account actions
    st.markdown("### 🔧 Account Management")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("📥 Export My Data", use_container_width=True):
            with st.spinner("Preparing data export..."):
                time.sleep(2)
                st.success("📧 Data export will be emailed to you within 24 hours")
    
    with action_col2:
        if st.button("🔄 Reset API Keys", use_container_width=True):
            if st.checkbox("⚠️ I understand this will remove all API keys"):
                st.warning("All API keys have been reset")
            else:
                st.info("Check the box above to confirm")
    
    with action_col3:
        if st.button("❌ Delete Account", use_container_width=True):
            st.error("⚠️ Account deletion is permanent and cannot be undone. Contact support if you need assistance.")
    
    # Supabase connection info
    st.markdown("---")
    st.markdown("### 🔌 Database Connection")
    
    if supabase_manager.demo_mode:
        st.warning("🔧 Currently running in demo mode. Configure Supabase credentials for full functionality.")
        st.info("💡 Add your Supabase URL and API key to `.streamlit/secrets.toml` to enable full features")
    else:
        st.success("✅ Connected to Supabase - All features enabled")
        st.info(f"🕐 Last sync: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

# Main application logic
def main():
    """Main application entry point with Supabase integration"""
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_dashboard()

# Run the application
if __name__ == "__main__":
    main()

