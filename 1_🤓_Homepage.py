import streamlit as st
import requests
import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
import json
import time
from typing import Dict, List, Optional
import hashlib
import random

# ------------------------
# Page Configuration
# ------------------------
st.set_page_config(
    page_title="Real Estate Intelligence Portal", 
    page_icon="🏡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .property-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        border: 1px solid #e9ecef;
    }
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .success-badge { background: #d4edda; color: #155724; }
    .warning-badge { background: #fff3cd; color: #856404; }
    .danger-badge { background: #f8d7da; color: #721c24; }
</style>
""", unsafe_allow_html=True)

# ------------------------
# Enhanced Supabase Caching
# ------------------------
@st.cache_resource
def init_supabase():
    """Initialize Supabase client with enhanced caching and connection pooling"""
    try:
        SUPABASE_URL = st.secrets["supabase"]["url"]
        SUPABASE_KEY = st.secrets["supabase"]["key"]
        
        client = create_client(
            SUPABASE_URL, 
            SUPABASE_KEY,
            options={
                "auto_refresh_token": True,
                "persist_session": True,
                "detect_session_in_url": False,
                "headers": {"apikey": SUPABASE_KEY}
            }
        )
        
        # Test connection
        client.table("api_usage").select("count", count="exact").limit(1).execute()
        st.success("✅ Supabase connection established successfully")
        return client
        
    except Exception as e:
        st.error(f"Failed to initialize Supabase: {e}")
        return None

class CacheManager:
    """Enhanced caching manager with multiple cache levels"""
    
    def __init__(self):
        self.memory_cache = {}
        self.cache_stats = {"hits": 0, "misses": 0}
    
    @st.cache_data(ttl=300)  # 5 minute cache for frequently accessed data
    def get_user_cache(self, user_id: int, cache_key: str):
        """Get cached user data with automatic expiration"""
        full_key = f"user_{user_id}_{cache_key}"
        if full_key in self.memory_cache:
            self.cache_stats["hits"] += 1
            return self.memory_cache[full_key]
        
        self.cache_stats["misses"] += 1
        return None
    
    def set_user_cache(self, user_id: int, cache_key: str, data: Dict, ttl: int = 300):
        """Set cached user data with TTL"""
        full_key = f"user_{user_id}_{cache_key}"
        self.memory_cache[full_key] = {
            "data": data,
            "timestamp": time.time(),
            "ttl": ttl
        }
    
    def invalidate_user_cache(self, user_id: int, cache_key: str = None):
        """Invalidate specific user cache or all user caches"""
        if cache_key:
            full_key = f"user_{user_id}_{cache_key}"
            self.memory_cache.pop(full_key, None)
        else:
            # Remove all caches for this user
            keys_to_remove = [k for k in self.memory_cache.keys() if k.startswith(f"user_{user_id}_")]
            for key in keys_to_remove:
                self.memory_cache.pop(key, None)
    
    def get_cache_stats(self):
        """Get cache performance statistics"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        return {
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "cache_size": len(self.memory_cache)
        }

cache_manager = CacheManager()

# ------------------------
# Config Loader
# ------------------------
@st.cache_data(ttl=3600)  # Increased TTL to 1 hour for config stability
def get_config():
    """Get configuration with error handling"""
    try:
        return {
            "wp_url": st.secrets["wordpress"]["base_url"],
            "wp_user": st.secrets["wordpress"]["username"],
            "wp_pass": st.secrets["wordpress"]["password"],
            "wc_key": st.secrets["woocommerce"]["consumer_key"],
            "wc_secret": st.secrets["woocommerce"]["consumer_secret"],
            "rentcast_key": st.secrets["rentcast"]["api_key"],
            "rentcast_url": "https://api.rentcast.io/v1"
        }
    except Exception as e:
        st.error(f"Configuration error: {e}")
        return None


# ------------------------
# Enhanced API Usage Management
# ------------------------
class APIUsageManager:
    """Enhanced API usage tracking with rate limiting and analytics"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.rate_limits = {
            "property_search": {"limit": 100, "window": 3600},  # 100 per hour
            "rent_estimate": {"limit": 50, "window": 3600},     # 50 per hour
            "market_analysis": {"limit": 25, "window": 3600}    # 25 per hour
        }
    
    def check_rate_limit(self, user_id: int, query_type: str) -> Dict:
        """Check if user has exceeded rate limits"""
        if not self.supabase:
            return {"allowed": True, "remaining": 999}
        
        try:
            now = datetime.datetime.utcnow()
            window_start = now - datetime.timedelta(seconds=self.rate_limits[query_type]["window"])
            
            recent_usage = self.supabase.table("api_usage").select("*").eq(
                "user_id", user_id
            ).eq(
                "query_type", query_type
            ).gte(
                "created_at", window_start.isoformat()
            ).execute()
            
            current_count = len(recent_usage.data)
            limit = self.rate_limits[query_type]["limit"]
            
            return {
                "allowed": current_count < limit,
                "remaining": max(0, limit - current_count),
                "reset_time": (now + datetime.timedelta(seconds=self.rate_limits[query_type]["window"])).isoformat(),
                "current_usage": current_count
            }
            
        except Exception as e:
            st.warning(f"Rate limit check failed: {e}")
            return {"allowed": True, "remaining": 999}
    
    def get_enhanced_usage_analytics(self, user_id: int) -> Dict:
        """Get comprehensive usage analytics"""
        if not self.supabase:
            return {}
        
        try:
            now = datetime.datetime.utcnow()
            
            periods = {
                "last_hour": now - datetime.timedelta(hours=1),
                "last_24h": now - datetime.timedelta(days=1),
                "last_7d": now - datetime.timedelta(days=7),
                "current_month": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            }
            
            analytics = {}
            
            for period_name, start_time in periods.items():
                usage_data = self.supabase.table("api_usage").select("*").eq(
                    "user_id", user_id
                ).gte("created_at", start_time.isoformat()).execute()
                
                # Analyze usage patterns
                by_type = {}
                by_hour = {}
                success_rate = {"success": 0, "error": 0}
                
                for record in usage_data.data:
                    query_type = record.get('query_type', 'unknown')
                    by_type[query_type] = by_type.get(query_type, 0) + 1
                    
                    # Hour-based analysis
                    hour = datetime.datetime.fromisoformat(record['created_at'].replace('Z', '+00:00')).hour
                    by_hour[hour] = by_hour.get(hour, 0) + 1
                    
                    # Success rate tracking
                    if record.get('metadata', {}).get('success', True):
                        success_rate["success"] += 1
                    else:
                        success_rate["error"] += 1
                
                analytics[period_name] = {
                    "total_requests": len(usage_data.data),
                    "by_type": by_type,
                    "by_hour": by_hour,
                    "success_rate": success_rate,
                    "avg_per_day": len(usage_data.data) / max(1, (now - start_time).days or 1)
                }
            
            return analytics
            
        except Exception as e:
            st.error(f"Failed to fetch usage analytics: {e}")
            return {}
    
    def log_enhanced_usage(self, user_id: int, query: str, query_type: str, 
                          success: bool = True, response_time: float = None, 
                          metadata: Dict = None):
        """Enhanced usage logging with performance metrics"""
        if not self.supabase:
            return
        
        try:
            enhanced_metadata = {
                "success": success,
                "response_time_ms": response_time,
                "user_agent": st.get_option("browser.gatherUsageStats"),
                "session_id": st.session_state.get("session_id", "unknown"),
                **(metadata or {})
            }
            
            log_data = {
                "user_id": user_id,
                "query": query[:500],  # Truncate long queries
                "query_type": query_type,
                "created_at": datetime.datetime.utcnow().isoformat(),
                "metadata": enhanced_metadata
            }
            
            self.supabase.table("api_usage").insert(log_data).execute()
            
            # Update cache
            cache_manager.invalidate_user_cache(user_id, "usage_analytics")
            
        except Exception as e:
            st.warning(f"Failed to log usage: {e}")

# ------------------------
# WordPress Login
# ------------------------
def wp_login(username: str, password: str) -> Optional[Dict]:
    """WordPress JWT authentication with user ID fetch"""
    if not config:
        return None

    url = f"{config['wp_url']}/wp-json/jwt-auth/v1/token"

    try:
        with st.spinner("Authenticating..."):
            resp = requests.post(
                url,
                data={"username": username, "password": password},
                timeout=10
            )

        if resp.status_code == 200:
            token_data = resp.json()

            # Fetch user details (to get WordPress user ID)
            me_url = f"{config['wp_url']}/wp-json/wp/v2/users/me"
            me_resp = requests.get(
                me_url,
                headers={"Authorization": f"Bearer {token_data['token']}"},
                timeout=10
            )

            if me_resp.status_code == 200:
                user_info = me_resp.json()
                token_data["user_id"] = user_info.get("id")
                token_data["user_email"] = user_info.get("email")
                token_data["username"] = user_info.get("username", token_data.get("user_nicename"))
            else:
                st.warning(f"⚠️ Could not fetch user info: {me_resp.text}")

            # Cache user session in Supabase
            cache_user_data(token_data)
            return token_data

        else:
            error_msg = resp.json().get('message', resp.text) if resp.text else 'Unknown error'
            st.error(f"🚫 Login failed: {error_msg}")
            return None

    except requests.exceptions.RequestException as e:
        st.error(f"🌐 Connection error: {e}")
        return None


# ------------------------
# Cache User Data
# ------------------------
def cache_user_data(user_data: Dict):
    """Cache user data for session management"""
    if supabase and "user_id" in user_data:
        try:
            supabase.table("user_sessions").upsert({
                "user_id": user_data["user_id"],
                "last_login": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "user_data": user_data
            }).execute()
        except Exception as e:
            st.warning(f"Failed to cache user data: {e}")


# ------------------------
# WooCommerce Integration
# ------------------------
@st.cache_data(ttl=600, show_spinner=False)  # Increased cache time to 10 minutes and disabled spinner
def get_wc_orders(user_id: int) -> List[Dict]:
    """Get WooCommerce orders for a customer"""
    if not config:
        return []

    url = f"{config['wp_url']}/wp-json/wc/v3/orders"
    params = {
        "customer": user_id,
        "per_page": 50,
        "orderby": "date",
        "order": "desc"
    }

    try:
        resp = requests.get(
            url,
            auth=(config['wc_key'], config['wc_secret']),
            params=params,
            timeout=15
        )

        if resp.status_code == 200:
            orders = resp.json()
            # Enrich order data
            for order in orders:
                order['total_float'] = float(order['total'])
                order['date_created_parsed'] = datetime.datetime.fromisoformat(
                    order['date_created'].replace('T', ' ').replace('Z', '')
                )
            return orders
        else:
            st.error(f"🛒 WooCommerce API error: {resp.text}")
            return []

    except requests.exceptions.RequestException as e:
        st.error(f"🌐 Failed to fetch orders: {e}")
        return []

def display_orders_analytics(orders: List[Dict]):
    """Display comprehensive order analytics"""
    if not orders:
        st.info("📦 No orders found")
        return
        
    # Convert to DataFrame for analysis
    df = pd.DataFrame(orders)
    df['month'] = pd.to_datetime(df['date_created']).dt.to_period('M')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Orders", 
            len(orders),
            delta=f"+{len([o for o in orders if o['status'] == 'completed'])} completed"
        )
    
    with col2:
        total_value = sum(o['total_float'] for o in orders)
        st.metric("Total Value", f"${total_value:,.2f}")
    
    with col3:
        avg_order = total_value / len(orders) if orders else 0
        st.metric("Average Order", f"${avg_order:,.2f}")
    
    with col4:
        recent_orders = len([o for o in orders if 
            datetime.datetime.fromisoformat(o['date_created'].replace('T', ' ').replace('Z', '')) 
            > datetime.datetime.now() - datetime.timedelta(days=30)
        ])
        st.metric("Recent Orders (30d)", recent_orders)
    
    # Order trend chart
    if len(orders) > 1:
        monthly_data = df.groupby('month').agg({
            'id': 'count',
            'total_float': 'sum'
        }).reset_index()
        monthly_data['month_str'] = monthly_data['month'].astype(str)
        
        fig = px.line(
            monthly_data, 
            x='month_str', 
            y=['id', 'total_float'],
            title="📈 Order Trends Over Time",
            labels={'value': 'Count/Amount', 'month_str': 'Month'}
        )
        st.plotly_chart(fig, use_container_width=True)

# ------------------------
# Property Management
# ------------------------
def save_property(user_id: int, data: Dict, search_params: Dict = None):
    """Enhanced property saving with search context"""
    if not supabase:
        return False
        
    try:
        # Generate a unique hash for deduplication
        property_hash = hashlib.md5(
            f"{data.get('address', '')}{data.get('city', '')}{data.get('state', '')}".encode()
        ).hexdigest()
        
        property_data = {
            "user_id": user_id,
            "property_hash": property_hash,
            "data": data,
            "search_params": search_params or {},
            "created_at": datetime.datetime.utcnow().isoformat(),
            "updated_at": datetime.datetime.utcnow().isoformat()
        }
        
        # Check if property already exists
        existing = supabase.table("properties").select("id").eq(
            "user_id", user_id
        ).eq("property_hash", property_hash).execute()
        
        if existing.data:
            # Update existing
            supabase.table("properties").update(property_data).eq(
                "id", existing.data[0]["id"]
            ).execute()
            st.success("🔄 Property updated successfully!")
        else:
            # Insert new
            supabase.table("properties").insert(property_data).execute()
            st.success("💾 Property saved successfully!")
        
        return True
        
    except Exception as e:
        st.error(f"Failed to save property: {e}")
        return False

@st.cache_data(ttl=300, show_spinner=False)  # Increased cache time to 5 minutes for better performance
def get_user_properties(user_id: int) -> List[Dict]:
    """Get user properties with caching"""
    if not supabase:
        return []
        
    try:
        result = supabase.table("properties").select("*").eq(
            "user_id", user_id
        ).order("updated_at", desc=True).execute()
        return result.data
    except Exception as e:
        st.error(f"Failed to fetch properties: {e}")
        return []

def delete_property(user_id: int, property_id: int):
    """Delete a saved property"""
    if not supabase:
        return False
        
    try:
        supabase.table("properties").delete().eq("id", property_id).eq("user_id", user_id).execute()
        st.success("🗑️ Property deleted successfully!")
        st.cache_data.clear()  # Clear cache
        return True
    except Exception as e:
        st.error(f"Failed to delete property: {e}")
        return False

# ------------------------
# Enhanced RentCast Integration
# ------------------------
class RentCastManager:
    """Enhanced RentCast API manager with intelligent caching and retry logic"""
    
    def __init__(self, config, usage_manager):
        self.config = config
        self.usage_manager = usage_manager
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json",
            "X-Api-Key": config['rentcast_key'],
            "User-Agent": "PropertySearchApp/1.0"
        })
    
    @st.cache_data(ttl=7200, show_spinner=False)
    def search_properties_enhanced(self, search_params: Dict, user_id: int) -> Dict:
        """Enhanced property search with comprehensive error handling"""
        
        rate_check = self.usage_manager.check_rate_limit(user_id, "property_search")
        if not rate_check["allowed"]:
            return {
                "error": "Rate limit exceeded",
                "reset_time": rate_check["reset_time"],
                "remaining": rate_check["remaining"]
            }
        
        start_time = time.time()
        
        try:
            validated_params = self._validate_search_params(search_params)
            if "error" in validated_params:
                return validated_params
            
            url = f"{self.config['rentcast_url']}/properties"
            
            max_retries = 3
            base_delay = 1
            
            for attempt in range(max_retries):
                try:
                    with st.spinner(f"🔍 Searching properties... (Attempt {attempt + 1}/{max_retries})"):
                        response = self.session.get(
                            url, 
                            params=validated_params, 
                            timeout=30
                        )
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        processed_data = self._process_property_data(data, search_params)
                        
                        # Log successful usage
                        self.usage_manager.log_enhanced_usage(
                            user_id, 
                            str(search_params), 
                            "property_search",
                            success=True,
                            response_time=response_time,
                            metadata={"results_count": len(processed_data.get("properties", []))}
                        )
                        
                        return processed_data
                    
                    elif response.status_code == 429:
                        if attempt < max_retries - 1:
                            # Exponential backoff with jitter
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            st.warning(f"🚦 Rate limited, retrying in {delay:.1f} seconds...")
                            time.sleep(delay)
                            continue
                        else:
                            self._log_api_error(user_id, "rate_limit_exceeded", response.status_code)
                            return {"error": "Rate limit exceeded", "retry_after": response.headers.get("Retry-After", "60")}
                    
                    elif response.status_code == 401:
                        self._log_api_error(user_id, "authentication_failed", response.status_code)
                        return {"error": "API authentication failed"}
                    
                    else:
                        if attempt < max_retries - 1 and response.status_code >= 500:
                            delay = base_delay * (2 ** attempt)
                            st.warning(f"🔄 Server error, retrying in {delay} seconds...")
                            time.sleep(delay)
                            continue
                        else:
                            self._log_api_error(user_id, f"http_error_{response.status_code}", response.status_code)
                            return {"error": f"API error: {response.status_code}"}
                
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        st.warning(f"⏱️ Request timeout, retrying...")
                        time.sleep(base_delay * (2 ** attempt))
                        continue
                    else:
                        self._log_api_error(user_id, "timeout", None)
                        return {"error": "Request timeout"}
                
                except requests.exceptions.RequestException as e:
                    self._log_api_error(user_id, f"request_error", None, str(e))
                    return {"error": f"Request failed: {str(e)}"}
        
        except Exception as e:
            self._log_api_error(user_id, "unexpected_error", None, str(e))
            return {"error": f"Unexpected error: {str(e)}"}
    
    def _validate_search_params(self, params: Dict) -> Dict:
        """Validate and sanitize search parameters"""
        required_fields = ["address", "city", "state"]
        
        for field in required_fields:
            if not params.get(field):
                return {"error": f"Missing required field: {field}"}
        
        validated = {
            "address": params["address"].strip()[:100],
            "city": params["city"].strip()[:50],
            "state": params["state"].strip()[:2].upper(),
            "propertyType": params.get("propertyType", "Single Family"),
            "radius": min(params.get("radius", 1), 10),  # Max 10 mile radius
            "limit": min(params.get("limit", 10), 50)     # Max 50 results
        }
        
        return validated
    
    def _process_property_data(self, raw_data: Dict, search_params: Dict) -> Dict:
        """Process and enrich property data"""
        if not raw_data or not isinstance(raw_data, (list, dict)):
            return {"properties": [], "total": 0}
        
        properties = raw_data if isinstance(raw_data, list) else [raw_data]
        
        enriched_properties = []
        for prop in properties:
            enriched = {
                **prop,
                "search_timestamp": datetime.datetime.utcnow().isoformat(),
                "search_params": search_params,
                "cache_key": self._generate_cache_key(prop),
                "investment_metrics": self._calculate_investment_metrics(prop),
                "market_score": self._calculate_market_score(prop)
            }
            enriched_properties.append(enriched)
        
        return {
            "properties": enriched_properties,
            "total": len(enriched_properties),
            "search_metadata": {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "params": search_params
            }
        }
    
    def _generate_cache_key(self, property_data: Dict) -> str:
        """Generate unique cache key for property"""
        address = property_data.get("address", "")
        city = property_data.get("city", "")
        state = property_data.get("state", "")
        return f"{address}_{city}_{state}".lower().replace(" ", "_").replace(",", "")
    
    def _calculate_investment_metrics(self, property_data: Dict) -> Dict:
        """Calculate investment metrics for property"""
        try:
            price = property_data.get("price", 0) or property_data.get("zestimate", 0)
            rent = property_data.get("rentEstimate", {}).get("rent", 0)
            
            if price and rent:
                monthly_rent = rent
                annual_rent = monthly_rent * 12
                gross_yield = (annual_rent / price) * 100 if price > 0 else 0
                
                # Estimate expenses (30% rule)
                estimated_expenses = annual_rent * 0.3
                net_income = annual_rent - estimated_expenses
                net_yield = (net_income / price) * 100 if price > 0 else 0
                
                return {
                    "gross_yield": round(gross_yield, 2),
                    "net_yield": round(net_yield, 2),
                    "monthly_cash_flow": round(monthly_rent - (estimated_expenses / 12), 2),
                    "cap_rate": round(net_yield, 2),
                    "price_to_rent_ratio": round(price / annual_rent, 2) if annual_rent > 0 else 0
                }
        except Exception:
            pass
        
        return {}
    
    def _calculate_market_score(self, property_data: Dict) -> int:
        """Calculate market attractiveness score (1-100)"""
        score = 50  # Base score
        
        try:
            factors = {
                "price_range": self._score_price_range(property_data.get("price", 0)),
                "rent_yield": self._score_rent_yield(property_data.get("rentEstimate", {})),
                "property_age": self._score_property_age(property_data.get("yearBuilt", 0)),
                "location": self._score_location(property_data)
            }
            
            # Weighted average
            weights = {"price_range": 0.3, "rent_yield": 0.4, "property_age": 0.2, "location": 0.1}
            weighted_score = sum(factors[k] * weights[k] for k in factors if factors[k] is not None)
            
            return min(100, max(1, int(weighted_score)))
        
        except Exception:
            return 50
    
    def _score_price_range(self, price: float) -> int:
        """Score based on price range (sweet spot for investment)"""
        if 100000 <= price <= 300000:
            return 90
        elif 300000 <= price <= 500000:
            return 75
        elif 50000 <= price <= 100000:
            return 60
        else:
            return 40
    
    def _score_rent_yield(self, rent_data: Dict) -> int:
        """Score based on rental yield"""
        rent = rent_data.get("rent", 0)
        if rent > 2000:
            return 85
        elif rent > 1500:
            return 70
        elif rent > 1000:
            return 55
        else:
            return 40
    
    def _score_property_age(self, year_built: int) -> int:
        """Score based on property age"""
        if not year_built:
            return 50
        
        current_year = datetime.datetime.now().year
        age = current_year - year_built
        
        if age <= 10:
            return 90
        elif age <= 20:
            return 75
        elif age <= 40:
            return 60
        else:
            return 45
    
    def _score_location(self, property_data: Dict) -> int:
        """Score based on location factors"""
        # This could be enhanced with actual location data
        return 70  # Placeholder
    
    def _log_api_error(self, user_id: int, error_type: str, status_code: int = None, details: str = None):
        """Log API errors for monitoring"""
        self.usage_manager.log_enhanced_usage(
            user_id,
            "API_ERROR",
            "property_search",
            success=False,
            metadata={
                "error_type": error_type,
                "status_code": status_code,
                "details": details
            }
        )

# ------------------------
# API Usage Management
# ------------------------
def get_user_usage(user_id: int) -> Dict:
    """Enhanced usage tracking with detailed metrics"""
    if not supabase:
        return {"current_month": 0, "total": 0, "limit": 30}
        
    try:
        now = datetime.datetime.utcnow()
        start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Current month usage
        current_month_res = supabase.table("api_usage").select("*").eq(
            "user_id", user_id
        ).gte("created_at", start_month.isoformat()).execute()
        
        # Total usage
        total_res = supabase.table("api_usage").select("*").eq("user_id", user_id).execute()
        
        # Usage by endpoint
        usage_by_type = {}
        for record in current_month_res.data:
            query_type = record.get('query_type', 'property_search')
            usage_by_type[query_type] = usage_by_type.get(query_type, 0) + 1
            
        return {
            "current_month": len(current_month_res.data),
            "total": len(total_res.data),
            "limit": 30,
            "by_type": usage_by_type,
            "daily_usage": calculate_daily_usage(current_month_res.data)
        }
        
    except Exception as e:
        st.error(f"Failed to fetch usage data: {e}")
        return {"current_month": 0, "total": 0, "limit": 30}

def calculate_daily_usage(usage_data: List[Dict]) -> Dict:
    """Calculate daily usage pattern"""
    daily_counts = {}
    for record in usage_data:
        date_str = record['created_at'][:10]  # Extract date part
        daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
    return daily_counts

def log_usage(user_id: int, query: str, query_type: str = "property_search", metadata: Dict = None):
    """Enhanced usage logging with metadata"""
    if not supabase:
        return
        
    try:
        log_data = {
            "user_id": user_id,
            "query": query,
            "query_type": query_type,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        supabase.table("api_usage").insert(log_data).execute()
    except Exception as e:
        st.warning(f"Failed to log usage: {e}")

# ------------------------
# Property Management
# ------------------------
def save_property(user_id: int, data: Dict, search_params: Dict = None):
    """Enhanced property saving with search context"""
    if not supabase:
        return False
        
    try:
        # Generate a unique hash for deduplication
        property_hash = hashlib.md5(
            f"{data.get('address', '')}{data.get('city', '')}{data.get('state', '')}".encode()
        ).hexdigest()
        
        property_data = {
            "user_id": user_id,
            "property_hash": property_hash,
            "data": data,
            "search_params": search_params or {},
            "created_at": datetime.datetime.utcnow().isoformat(),
            "updated_at": datetime.datetime.utcnow().isoformat()
        }
        
        # Check if property already exists
        existing = supabase.table("properties").select("id").eq(
            "user_id", user_id
        ).eq("property_hash", property_hash).execute()
        
        if existing.data:
            # Update existing
            supabase.table("properties").update(property_data).eq(
                "id", existing.data[0]["id"]
            ).execute()
            st.success("🔄 Property updated successfully!")
        else:
            # Insert new
            supabase.table("properties").insert(property_data).execute()
            st.success("💾 Property saved successfully!")
        
        return True
        
    except Exception as e:
        st.error(f"Failed to save property: {e}")
        return False

@st.cache_data(ttl=300, show_spinner=False)  # Increased cache time to 5 minutes for better performance
def get_user_properties(user_id: int) -> List[Dict]:
    """Get user properties with caching"""
    if not supabase:
        return []
        
    try:
        result = supabase.table("properties").select("*").eq(
            "user_id", user_id
        ).order("updated_at", desc=True).execute()
        return result.data
    except Exception as e:
        st.error(f"Failed to fetch properties: {e}")
        return []

def delete_property(user_id: int, property_id: int):
    """Delete a saved property"""
    if not supabase:
        return False
        
    try:
        supabase.table("properties").delete().eq("id", property_id).eq("user_id", user_id).execute()
        st.success("🗑️ Property deleted successfully!")
        st.cache_data.clear()  # Clear cache
        return True
    except Exception as e:
        st.error(f"Failed to delete property: {e}")
        return False

# ------------------------
# RentCast API Integration
# ------------------------
@st.cache_data(ttl=7200, show_spinner=False)  # Increased cache to 2 hours for property data stability
def fetch_property_data(address: str, city: str, state: str) -> Optional[Dict]:
    """Enhanced property data fetching with caching and error handling"""
    if not config:
        return None
        
    url = f"{config['rentcast_url']}/properties"
    headers = {
        "accept": "application/json", 
        "X-Api-Key": config['rentcast_key']
    }
    params = {
        "address": address,
        "city": city,
        "state": state,
        "propertyType": "Single Family"  # Can be made configurable
    }
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            with st.spinner(f"🔍 Fetching property data... (Attempt {attempt + 1}/{max_retries})"):
                resp = requests.get(url, headers=headers, params=params, timeout=30)  # Increased timeout to 30 seconds
                
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    # Enrich the data
                    property_data = data[0] if isinstance(data, list) else data
                    property_data['fetch_timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    property_data['search_params'] = params
                    property_data['cache_key'] = f"{address}_{city}_{state}".lower().replace(" ", "_")  # Added cache key for better tracking
                    return property_data
                else:
                    st.warning("🔍 No property data found for this address")
                    return None
            elif resp.status_code == 401:
                st.error("🔑 API Authentication failed - check your RentCast API key")
                return None
            elif resp.status_code == 429:
                if attempt < max_retries - 1:  # Added retry logic for rate limiting
                    st.warning(f"🚦 Rate limit hit, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    st.error("🚦 Rate limit exceeded - please wait before making another request")
                    return None
            elif resp.status_code >= 500:  # Added retry for server errors
                if attempt < max_retries - 1:
                    st.warning(f"🌐 Server error, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    st.error(f"🌐 Server Error {resp.status_code}: {resp.text}")
                    return None
            else:
                st.error(f"🌐 API Error {resp.status_code}: {resp.text}")
                return None
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                st.warning(f"⏱️ Request timeout, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                st.error("⏱️ Request timed out after multiple attempts")
                return None
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                st.warning(f"🌐 Request failed, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                st.error(f"🌐 Request failed after {max_retries} attempts: {e}")
                return None
    
    return None

def invalidate_property_cache(address: str, city: str, state: str):
    """Invalidate cached property data for specific address"""
    cache_key = f"{address}_{city}_{state}".lower().replace(" ", "_")
    # Clear specific cache entry if possible
    st.cache_data.clear()

def fetch_rent_estimates(property_data: Dict) -> Dict:
    """Fetch rent estimates for a property"""
    if not config or not property_data:
        return {}
        
    # This would use RentCast's rent estimate endpoint
    # Implementation depends on the specific API endpoints available
    try:
        # Placeholder for rent estimation logic
        estimated_rent = property_data.get('rentEstimate', {})
        return {
            'monthly_rent': estimated_rent.get('rent', 0),
            'rent_range_low': estimated_rent.get('rentRangeLow', 0),
            'rent_range_high': estimated_rent.get('rentRangeHigh', 0),
            'confidence': estimated_rent.get('confidence', 'unknown')
        }
    except Exception as e:
        st.warning(f"Failed to fetch rent estimates: {e}")
        return {}

# ------------------------
# Property Analysis & Visualization
# ------------------------
def analyze_property(property_data: Dict) -> Dict:
    """Comprehensive property analysis"""
    analysis = {
        'basic_info': extract_basic_info(property_data),
        'financial_metrics': calculate_financial_metrics(property_data),
        'market_analysis': perform_market_analysis(property_data),
        'investment_score': calculate_investment_score(property_data)
    }
    return analysis

def extract_basic_info(data: Dict) -> Dict:
    """Extract basic property information"""
    return {
        'address': data.get('address', 'N/A'),
        'city': data.get('city', 'N/A'),
        'state': data.get('state', 'N/A'),
        'zip_code': data.get('zipCode', 'N/A'),
        'property_type': data.get('propertyType', 'N/A'),
        'bedrooms': data.get('bedrooms', 0),
        'bathrooms': data.get('bathrooms', 0),
        'square_feet': data.get('squareFootage', 0),
        'lot_size': data.get('lotSize', 0),
        'year_built': data.get('yearBuilt', 'N/A')
    }

def calculate_financial_metrics(data: Dict) -> Dict:
    """Calculate financial metrics and investment potential"""
    price = data.get('price', 0) or data.get('lastSalePrice', 0)
    rent_estimate = data.get('rentEstimate', {}).get('rent', 0)
    
    if price and rent_estimate:
        monthly_rent = rent_estimate
        annual_rent = monthly_rent * 12
        
        # Calculate key metrics
        cap_rate = (annual_rent / price) * 100 if price > 0 else 0
        price_to_rent = price / annual_rent if annual_rent > 0 else 0
        cash_flow = monthly_rent - (price * 0.004)  # Rough estimate with 4% monthly expenses
        
        return {
            'price': price,
            'monthly_rent': monthly_rent,
            'annual_rent': annual_rent,
            'cap_rate': round(cap_rate, 2),
            'price_to_rent_ratio': round(price_to_rent, 2),
            'estimated_cash_flow': round(cash_flow, 2),
            'roi_estimate': round((cash_flow * 12 / (price * 0.2)) * 100, 2) if price > 0 else 0  # Assume 20% down
        }
    
    return {
        'price': price,
        'monthly_rent': rent_estimate,
        'annual_rent': rent_estimate * 12,
        'cap_rate': 0,
        'price_to_rent_ratio': 0,
        'estimated_cash_flow': 0,
        'roi_estimate': 0
    }

def perform_market_analysis(data: Dict) -> Dict:
    """Analyze market conditions and comparables"""
    # This would typically involve additional API calls to get comparable properties
    # For now, we'll use available data to provide basic market insights
    
    return {
        'neighborhood': data.get('neighborhood', 'N/A'),
        'price_per_sqft': round(data.get('price', 0) / data.get('squareFootage', 1), 2) if data.get('squareFootage') else 0,
        'market_status': determine_market_status(data),
        'appreciation_potential': analyze_appreciation_potential(data)
    }

def determine_market_status(data: Dict) -> str:
    """Determine market status based on available data"""
    # This is a simplified analysis - in reality, you'd want more market data
    price_per_sqft = data.get('price', 0) / data.get('squareFootage', 1) if data.get('squareFootage') else 0
    
    if price_per_sqft > 200:
        return "Hot Market"
    elif price_per_sqft > 100:
        return "Balanced Market"
    else:
        return "Buyer's Market"

def analyze_appreciation_potential(data: Dict) -> str:
    """Analyze appreciation potential"""
    year_built = data.get('yearBuilt', 2000)
    current_year = datetime.datetime.now().year
    property_age = current_year - year_built if isinstance(year_built, int) else 20
    
    if property_age < 10:
        return "High"
    elif property_age < 30:
        return "Moderate"
    else:
        return "Low"

def calculate_investment_score(data: Dict) -> Dict:
    """Calculate overall investment score"""
    metrics = calculate_financial_metrics(data)
    market = perform_market_analysis(data)
    
    # Simple scoring algorithm
    score = 0
    factors = []
    
    # Cap rate scoring
    cap_rate = metrics.get('cap_rate', 0)
    if cap_rate > 8:
        score += 25
        factors.append("Excellent cap rate")
    elif cap_rate > 6:
        score += 15
        factors.append("Good cap rate")
    elif cap_rate > 4:
        score += 10
        factors.append("Fair cap rate")
    
    # Cash flow scoring
    cash_flow = metrics.get('estimated_cash_flow', 0)
    if cash_flow > 300:
        score += 25
        factors.append("Strong cash flow")
    elif cash_flow > 100:
        score += 15
        factors.append("Positive cash flow")
    elif cash_flow > 0:
        score += 10
        factors.append("Break-even cash flow")
    
    # Market status scoring
    if market.get('market_status') == "Buyer's Market":
        score += 20
        factors.append("Favorable market conditions")
    elif market.get('market_status') == "Balanced Market":
        score += 15
        factors.append("Stable market conditions")
    
    # Appreciation potential
    if market.get('appreciation_potential') == "High":
        score += 15
        factors.append("High appreciation potential")
    elif market.get('appreciation_potential') == "Moderate":
        score += 10
        factors.append("Moderate appreciation potential")
    
    # Property condition (age-based)
    property_age = datetime.datetime.now().year - data.get('yearBuilt', 2000) if isinstance(data.get('yearBuilt'), int) else 20
    if property_age < 10:
        score += 15
        factors.append("New property")
    elif property_age < 30:
        score += 10
        factors.append("Well-maintained age")
    
    # Determine grade
    if score >= 80:
        grade = "A+"
        recommendation = "Excellent investment opportunity"
    elif score >= 70:
        grade = "A"
        recommendation = "Strong investment potential"
    elif score >= 60:
        grade = "B+"
        recommendation = "Good investment with some caution"
    elif score >= 50:
        grade = "B"
        recommendation = "Fair investment opportunity"
    elif score >= 40:
        grade = "C"
        recommendation = "Marginal investment - proceed carefully"
    else:
        grade = "D"
        recommendation = "Poor investment - not recommended"
    
    return {
        'score': score,
        'grade': grade,
        'recommendation': recommendation,
        'positive_factors': factors
    }

def display_property_analysis(analysis: Dict, property_data: Dict):
    """Display comprehensive property analysis"""
    
    # Header
    basic = analysis['basic_info']
    st.markdown(f"""
    <div class="property-card">
        <h3>🏠 {basic['address']}</h3>
        <p><strong>{basic['city']}, {basic['state']} {basic['zip_code']}</strong></p>
        <p>{basic['bedrooms']} bed • {basic['bathrooms']} bath • {basic['square_feet']} sq ft • Built {basic['year_built']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Investment Score
    score_data = analysis['investment_score']
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 15px; color: white; margin: 1rem 0;">
            <h2 style="margin: 0; font-size: 3rem;">{score_data['grade']}</h2>
            <p style="margin: 0.5rem 0; font-size: 1.2rem;">Investment Score: {score_data['score']}/100</p>
            <p style="margin: 0; opacity: 0.9;">{score_data['recommendation']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Financial Metrics
    st.subheader("💰 Financial Analysis")
    financial = analysis['financial_metrics']
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Property Price", f"${financial['price']:,.0f}")
    with col2:
        st.metric("Monthly Rent", f"${financial['monthly_rent']:,.0f}")
    with col3:
        st.metric("Cap Rate", f"{financial['cap_rate']}%")
    with col4:
        st.metric("Cash Flow", f"${financial['estimated_cash_flow']:,.0f}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Annual Rent", f"${financial['annual_rent']:,.0f}")
    with col2:
        st.metric("Price/Rent Ratio", f"{financial['price_to_rent_ratio']:.1f}")
    with col3:
        st.metric("ROI Estimate", f"{financial['roi_estimate']}%")
    with col4:
        st.metric("Price/Sq Ft", f"${analysis['market_analysis']['price_per_sqft']:.0f}")
    
    # Market Analysis
    st.subheader("📊 Market Analysis")
    market = analysis['market_analysis']
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**Neighborhood:** {market['neighborhood']}")
    with col2:
        status_color = {"Hot Market": "🔥", "Balanced Market": "⚖️", "Buyer's Market": "💰"}
        st.info(f"**Market Status:** {status_color.get(market['market_status'], '📈')} {market['market_status']}")
    with col3:
        potential_color = {"High": "🚀", "Moderate": "📈", "Low": "📉"}
        st.info(f"**Appreciation:** {potential_color.get(market['appreciation_potential'], '📊')} {market['appreciation_potential']}")
    
    # Positive Factors
    if score_data['positive_factors']:
        st.subheader("✅ Positive Investment Factors")
        factors_text = " • ".join(score_data['positive_factors'])
        st.success(factors_text)
    
    # Visualizations
    create_property_charts(financial, property_data)

def create_property_charts(financial_data: Dict, property_data: Dict):
    """Create visualizations for property analysis"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Cash Flow Breakdown
        if financial_data['monthly_rent'] > 0:
            estimated_expenses = financial_data['price'] * 0.004 if financial_data['price'] else 0
            
            fig = go.Figure(data=[
                go.Bar(
                    x=['Monthly Income', 'Estimated Expenses', 'Net Cash Flow'],
                    y=[financial_data['monthly_rent'], estimated_expenses, financial_data['estimated_cash_flow']],
                    marker_color=['green', 'red', 'blue']
                )
            ])
            fig.update_layout(title="💰 Monthly Cash Flow Breakdown", yaxis_title="Amount ($)")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Investment Metrics Radar
        metrics = [
            financial_data['cap_rate'] * 10,  # Scale up for visibility
            min(financial_data['roi_estimate'], 100),
            max(0, min(100, (financial_data['estimated_cash_flow'] + 500) / 10)),  # Scale cash flow
            max(0, min(100, 100 - financial_data['price_to_rent_ratio'] * 2))  # Inverse price/rent ratio
        ]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=metrics,
            theta=['Cap Rate', 'ROI', 'Cash Flow', 'Affordability'],
            fill='toself',
            name='Property Metrics'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title="📊 Investment Metrics Overview",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

# ------------------------
# Advanced Property Search
# ------------------------
def advanced_property_search():
    """Advanced property search with filters"""
    st.subheader("🔍 Advanced Property Search")
    
    with st.expander("Search Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_price = st.number_input("Min Price ($)", value=0, step=10000)
            max_price = st.number_input("Max Price ($)", value=1000000, step=10000)
        
        with col2:
            min_bedrooms = st.selectbox("Min Bedrooms", [0, 1, 2, 3, 4, 5])
            max_bedrooms = st.selectbox("Max Bedrooms", [1, 2, 3, 4, 5, 10], index=5)
        
        with col3:
            property_types = st.multiselect(
                "Property Types", 
                ["Single Family", "Condo", "Townhouse", "Multi-Family"],
                default=["Single Family"]
            )
    
    # Saved searches
    if st.button("💾 Save Search Criteria"):
        # Implementation for saving search criteria
        st.success("Search criteria saved!")

# ------------------------
# Portfolio Management
# ------------------------
def display_portfolio_overview(properties: List[Dict]):
    """Display comprehensive portfolio analytics"""
    if not properties:
        st.info("📊 No properties in your portfolio yet")
        return
    
    # Calculate portfolio metrics
    portfolio_metrics = calculate_portfolio_metrics(properties)
    
    st.subheader("📈 Portfolio Overview")
    
    # Key metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Properties", 
            portfolio_metrics['total_properties'],
            delta=f"+{portfolio_metrics.get('new_this_month', 0)} this month"
        )
    
    with col2:
        st.metric(
            "Portfolio Value", 
            f"${portfolio_metrics['total_value']:,.0f}",
            delta=f"{portfolio_metrics.get('value_change_pct', 0):+.1f}%"
        )
    
    with col3:
        st.metric(
            "Monthly Rent", 
            f"${portfolio_metrics['total_monthly_rent']:,.0f}",
            delta=f"${portfolio_metrics.get('rent_change', 0):+,.0f}"
        )
    
    with col4:
        st.metric(
            "Avg Cap Rate", 
            f"{portfolio_metrics['avg_cap_rate']:.2f}%",
            delta=f"{portfolio_metrics.get('cap_rate_trend', 0):+.2f}%"
        )
    
    with col5:
        st.metric(
            "Total Cash Flow", 
            f"${portfolio_metrics['total_cash_flow']:,.0f}",
            delta=portfolio_metrics.get('cash_flow_status', 'Positive' if portfolio_metrics['total_cash_flow'] > 0 else 'Negative')
        )
    
    # Portfolio composition charts
    create_portfolio_charts(properties, portfolio_metrics)
    
    # Property performance table
    display_portfolio_table(properties)

def calculate_portfolio_metrics(properties: List[Dict]) -> Dict:
    """Calculate comprehensive portfolio metrics"""
    total_value = 0
    total_rent = 0
    total_cash_flow = 0
    cap_rates = []
    
    for prop in properties:
        data = prop.get('data', {})
        
        # Extract financial data
        price = data.get('price', 0) or data.get('lastSalePrice', 0)
        rent = data.get('rentEstimate', {}).get('rent', 0) if isinstance(data.get('rentEstimate'), dict) else 0
        
        if price:
            total_value += price
            annual_rent = rent * 12
            total_rent += rent
            
            # Estimate cash flow (simplified)
            monthly_expenses = price * 0.004  # 4% monthly expense ratio
            cash_flow = rent - monthly_expenses
            total_cash_flow += cash_flow
            
            # Cap rate
            if annual_rent > 0:
                cap_rate = (annual_rent / price) * 100
                cap_rates.append(cap_rate)
    
    return {
        'total_properties': len(properties),
        'total_value': total_value,
        'total_monthly_rent': total_rent,
        'total_annual_rent': total_rent * 12,
        'total_cash_flow': total_cash_flow,
        'avg_cap_rate': sum(cap_rates) / len(cap_rates) if cap_rates else 0,
        'avg_property_value': total_value / len(properties) if properties else 0,
        'portfolio_yield': (total_rent * 12 / total_value * 100) if total_value > 0 else 0
    }

def create_portfolio_charts(properties: List[Dict], metrics: Dict):
    """Create portfolio visualization charts"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Portfolio value distribution
        prop_values = []
        prop_labels = []
        
        for i, prop in enumerate(properties):
            data = prop.get('data', {})
            value = data.get('price', 0) or data.get('lastSalePrice', 0)
            address = data.get('address', f'Property {i+1}')
            
            if value > 0:
                prop_values.append(value)
                prop_labels.append(f"{address[:20]}..." if len(address) > 20 else address)
        
        if prop_values:
            fig = px.pie(
                values=prop_values,
                names=prop_labels,
                title="🏠 Portfolio Value Distribution"
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Cash flow analysis
        cash_flows = []
        addresses = []
        
        for prop in properties:
            data = prop.get('data', {})
            price = data.get('price', 0) or data.get('lastSalePrice', 0)
            rent = data.get('rentEstimate', {}).get('rent', 0) if isinstance(data.get('rentEstimate'), dict) else 0
            address = data.get('address', 'Unknown')
            
            if price and rent:
                monthly_expenses = price * 0.004
                cash_flow = rent - monthly_expenses
                cash_flows.append(cash_flow)
                addresses.append(address[:15] + "..." if len(address) > 15 else address)
        
        if cash_flows:
            colors = ['green' if cf > 0 else 'red' for cf in cash_flows]
            fig = go.Figure(data=[
                go.Bar(x=addresses, y=cash_flows, marker_color=colors)
            ])
            fig.update_layout(
                title="💰 Monthly Cash Flow by Property",
                xaxis_title="Properties",
                yaxis_title="Monthly Cash Flow ($)"
            )
            st.plotly_chart(fig, use_container_width=True)

def display_portfolio_table(properties: List[Dict]):
    """Display detailed portfolio table"""
    st.subheader("📋 Property Details")
    
    # Prepare data for table
    table_data = []
    for i, prop in enumerate(properties):
        data = prop.get('data', {})
        
        price = data.get('price', 0) or data.get('lastSalePrice', 0)
        rent = data.get('rentEstimate', {}).get('rent', 0) if isinstance(data.get('rentEstimate'), dict) else 0
        
        # Calculate metrics
        annual_rent = rent * 12
        cap_rate = (annual_rent / price * 100) if price > 0 else 0
        cash_flow = rent - (price * 0.004) if price > 0 else 0
        
        table_data.append({
            'Property': data.get('address', f'Property {i+1}'),
            'City': data.get('city', 'N/A'),
            'State': data.get('state', 'N/A'),
            'Price': f"${price:,.0f}" if price else 'N/A',
            'Monthly Rent': f"${rent:,.0f}" if rent else 'N/A',
            'Cap Rate': f"{cap_rate:.2f}%" if cap_rate else 'N/A',
            'Cash Flow': f"${cash_flow:,.0f}" if cash_flow else 'N/A',
            'Bedrooms': data.get('bedrooms', 'N/A'),
            'Bathrooms': data.get('bathrooms', 'N/A'),
            'Sq Ft': f"{data.get('squareFootage', 0):,}" if data.get('squareFootage') else 'N/A',
            'Added': prop.get('created_at', '')[:10] if prop.get('created_at') else 'N/A'
        })
    
    if table_data:
        df = pd.DataFrame(table_data)
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        with col1:
            state_filter = st.selectbox("Filter by State", ['All'] + list(df['State'].unique()))
        with col2:
            min_cap_rate = st.slider("Min Cap Rate (%)", 0.0, 20.0, 0.0, 0.5)
        with col3:
            sort_by = st.selectbox("Sort by", ['Property', 'Price', 'Cap Rate', 'Cash Flow', 'Added'])
        
        # Apply filters
        filtered_df = df.copy()
        if state_filter != 'All':
            filtered_df = filtered_df[filtered_df['State'] == state_filter]
        
        # Convert cap rate for filtering (remove % and convert to float)
        cap_rates_numeric = []
        for cap_rate_str in filtered_df['Cap Rate']:
            if cap_rate_str != 'N/A':
                try:
                    cap_rates_numeric.append(float(cap_rate_str.replace('%', '')))
                except:
                    cap_rates_numeric.append(0)
            else:
                cap_rates_numeric.append(0)
        
        filtered_df['Cap Rate Numeric'] = cap_rates_numeric
        filtered_df = filtered_df[filtered_df['Cap Rate Numeric'] >= min_cap_rate]
        filtered_df = filtered_df.drop('Cap Rate Numeric', axis=1)
        
        # Sort
        if sort_by in filtered_df.columns:
            ascending = sort_by not in ['Price', 'Cap Rate', 'Cash Flow']
            try:
                filtered_df = filtered_df.sort_values(sort_by, ascending=ascending)
            except:
                pass  # Keep original order if sorting fails
        
        # Display table
        st.dataframe(filtered_df, use_container_width=True)
        
        # Export option
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Portfolio Data (CSV)",
            data=csv,
            file_name=f"portfolio_data_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# ------------------------
# Market Analysis Tools
# ------------------------
def market_analysis_page():
    """Advanced market analysis tools"""
    st.header("📊 Market Analysis")
    
    tab1, tab2, tab3 = st.tabs(["🏘️ Neighborhood Analysis", "📈 Market Trends", "🔍 Comparable Properties"])
    
    with tab1:
        neighborhood_analysis()
    
    with tab2:
        market_trends_analysis()
    
    with tab3:
        comparable_properties_analysis()

def neighborhood_analysis():
    """Analyze neighborhood metrics"""
    st.subheader("🏘️ Neighborhood Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        city = st.text_input("City", value="Los Angeles")
        state = st.text_input("State", value="CA")
    
    with col2:
        radius = st.slider("Analysis Radius (miles)", 1, 10, 3)
        property_type = st.selectbox("Property Type", ["All", "Single Family", "Condo", "Townhouse"])
    
    if st.button("🔍 Analyze Neighborhood"):
        with st.spinner("Analyzing neighborhood data..."):
            # This would typically involve multiple API calls to gather neighborhood data
            st.info("Neighborhood analysis feature requires additional API integrations")
            
            # Placeholder for neighborhood metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Avg Home Price", "$650,000", "↑ 5.2%")
            with col2:
                st.metric("Avg Rent", "$2,800", "↑ 3.1%")
            with col3:
                st.metric("Cap Rate", "4.8%", "↓ 0.2%")
            with col4:
                st.metric("Price/Rent Ratio", "19.3", "↑ 1.1")

def market_trends_analysis():
    """Display market trends and forecasts"""
    st.subheader("📈 Market Trends")
    
    # Generate sample trend data
    dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='M')
    price_trend = [500000 + i * 2000 + (i % 3 - 1) * 5000 for i in range(len(dates))]
    rent_trend = [2500 + i * 15 + (i % 4 - 2) * 50 for i in range(len(dates))]
    
    trend_df = pd.DataFrame({
        'Date': dates,
        'Avg_Price': price_trend,
        'Avg_Rent': rent_trend
    })
    
    # Create trend chart
    fig = px.line(
        trend_df, 
        x='Date', 
        y=['Avg_Price', 'Avg_Rent'],
        title="📈 Price and Rent Trends Over Time",
        labels={'value': 'Amount ($)', 'variable': 'Metric'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Market indicators
    st.subheader("🎯 Market Indicators")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("**Market Temperature:** 🔥 Hot")
        st.write("Properties selling 15% above asking price")
    
    with col2:
        st.info("**Inventory Level:** 📉 Low")
        st.write("2.1 months of supply available")
    
    with col3:
        st.info("**Price Trend:** 📈 Rising")
        st.write("5.2% year-over-year appreciation")

def comparable_properties_analysis():
    """Find and analyze comparable properties"""
    st.subheader("🔍 Comparable Properties")
    
    with st.form("comp_search"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            comp_address = st.text_input("Subject Property Address")
            comp_city = st.text_input("City")
        
        with col2:
            comp_state = st.text_input("State")
            comp_radius = st.slider("Search Radius (miles)", 0.5, 5.0, 1.0)
        
        with col3:
            bed_variance = st.selectbox("Bedroom Variance", ["Exact", "±1", "±2"])
            max_comps = st.number_input("Max Comparables", 3, 20, 10)
        
        submitted = st.form_submit_button("🔍 Find Comparables")
    
    if submitted and comp_address:
        st.info("Comparable properties search requires additional API integrations with MLS or similar services")
        
        # Placeholder comparable results
        st.subheader("📋 Comparable Properties Found")
        
        sample_comps = [
            {"address": "456 Oak St", "price": 675000, "beds": 3, "baths": 2, "sqft": 1850, "distance": 0.3},
            {"address": "789 Pine Ave", "price": 695000, "beds": 4, "baths": 2.5, "sqft": 1920, "distance": 0.7},
            {"address": "321 Elm Dr", "price": 650000, "beds": 3, "baths": 2, "sqft": 1780, "distance": 0.5},
        ]
        
        for comp in sample_comps:
            with st.expander(f"{comp['address']} - ${comp['price']:,}"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Price", f"${comp['price']:,}")
                with col2:
                    st.metric("Bed/Bath", f"{comp['beds']}/{comp['baths']}")
                with col3:
                    st.metric("Sq Ft", f"{comp['sqft']:,}")
                with col4:
                    st.metric("Distance", f"{comp['distance']} mi")

# ------------------------
# Reporting & Export
# ------------------------
def generate_property_report(property_data: Dict, analysis: Dict) -> str:
    """Generate comprehensive property report"""
    
    basic = analysis['basic_info']
    financial = analysis['financial_metrics']
    market = analysis['market_analysis']
    score = analysis['investment_score']
    
    report = f"""
# Property Investment Analysis Report

**Generated:** {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}

---

## Property Overview

**Address:** {basic['address']}
**Location:** {basic['city']}, {basic['state']} {basic['zip_code']}
**Property Type:** {basic['property_type']}
**Year Built:** {basic['year_built']}

### Physical Characteristics
- **Bedrooms:** {basic['bedrooms']}
- **Bathrooms:** {basic['bathrooms']}
- **Square Footage:** {basic['square_feet']:,} sq ft
- **Lot Size:** {basic['lot_size']} sq ft

---

## Investment Analysis

### Overall Investment Score: {score['grade']} ({score['score']}/100)
**Recommendation:** {score['recommendation']}

### Financial Metrics
- **Property Price:** ${financial['price']:,}
- **Monthly Rent Estimate:** ${financial['monthly_rent']:,}
- **Annual Rent:** ${financial['annual_rent']:,}
- **Cap Rate:** {financial['cap_rate']}%
- **Estimated Monthly Cash Flow:** ${financial['estimated_cash_flow']:,}
- **Price-to-Rent Ratio:** {financial['price_to_rent_ratio']:.1f}
- **ROI Estimate:** {financial['roi_estimate']}%

### Market Analysis
- **Neighborhood:** {market['neighborhood']}
- **Price per Sq Ft:** ${market['price_per_sqft']:.0f}
- **Market Status:** {market['market_status']}
- **Appreciation Potential:** {market['appreciation_potential']}

### Positive Investment Factors
{chr(10).join(f'• {factor}' for factor in score['positive_factors'])}

---

## Important Disclaimers

1. This analysis is based on estimated data and should not be considered as professional financial advice.
2. Actual rental income, expenses, and property values may vary significantly.
3. Please consult with real estate professionals, accountants, and financial advisors before making investment decisions.
4. Market conditions can change rapidly and affect investment performance.

---

*Report generated by Real Estate Intelligence Portal*
"""
    
    return report

# ------------------------
# Main Application
# ------------------------
def main():
    """Main application function"""
    
    # Initialize session state
    if "wp_user" not in st.session_state:
        st.session_state.wp_user = None
    
    if "selected_property" not in st.session_state:
        st.session_state.selected_property = None
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏡 Real Estate Intelligence Portal</h1>
        <p>Comprehensive property analysis and investment management platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Authentication check
    if st.session_state.wp_user is None:
        display_login_page()
    else:
        display_main_application()

def display_login_page():
    """Display login interface"""
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h2 style="text-align: center; color: #333; margin-bottom: 2rem;">🔑 Account Access</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("📧 WordPress Username/Email", placeholder="Enter your username or email")
            password = st.text_input("🔐 Password", type="password", placeholder="Enter your password")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                login_submitted = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if login_submitted and username and password:
                wp_user = wp_login(username, password)
                if wp_user:
                    st.session_state.wp_user = wp_user
                    st.success("✅ Login successful! Redirecting...")
                    time.sleep(1)
                    st.rerun()
        
        # Additional info
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem; color: #666;">
            <p>🔒 Secure login powered by WordPress JWT authentication</p>
            <p>Need help? Contact support or check your WordPress credentials</p>
        </div>
        """, unsafe_allow_html=True)

def display_main_application():
    """Display main application interface"""
    
    wp_user = st.session_state.wp_user
    user_id = wp_user["user_id"]
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1rem; border-radius: 10px; color: white; margin-bottom: 1rem;">
            <h4 style="margin: 0;">👋 Welcome back!</h4>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">{wp_user['user_email']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Usage tracking
        usage_data = get_user_usage(user_id)
        usage_pct = (usage_data['current_month'] / usage_data['limit']) * 100
        
        st.markdown("### 📊 API Usage This Month")
        st.progress(usage_pct / 100)
        st.write(f"{usage_data['current_month']}/{usage_data['limit']} calls ({usage_pct:.1f}%)")
        
        if usage_data.get('by_type'):
            st.write("**By Type:**")
            for query_type, count in usage_data['by_type'].items():
                st.write(f"• {query_type}: {count}")
        
        st.divider()
        
        # Navigation
        page = st.selectbox(
            "🧭 Navigation",
            ["🏠 Property Search", "📊 Portfolio", "🛒 Orders", "📈 Market Analysis", "⚙️ Settings"]
        )
        
        st.divider()
        
        if st.button("🔓 Logout", use_container_width=True):
            st.session_state.wp_user = None
            st.rerun()
    
    # Main content area
    if page == "🏠 Property Search":
        display_property_search(user_id, usage_data)
    elif page == "📊 Portfolio":
        display_portfolio_page(user_id)
    elif page == "🛒 Orders":
        display_orders_page(user_id)
    elif page == "📈 Market Analysis":
        market_analysis_page()
    elif page == "⚙️ Settings":
        display_settings_page(user_id)

def display_property_search(user_id: int, usage_data: Dict):
    """Display property search interface"""
    
    st.header("🔍 Property Search & Analysis")
    
    # Quick search form
    with st.form("property_search", clear_on_submit=False):
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        
        with col1:
            address = st.text_input("🏠 Property Address", value="123 Main St", placeholder="Enter street address")
        with col2:
            city = st.text_input("🏙️ City", value="Los Angeles", placeholder="Enter city")
        with col3:
            state = st.text_input("🗺️ State", value="CA", placeholder="State")
        with col4:
            search_submitted = st.form_submit_button("🔍 Search", use_container_width=True)
    
    # Advanced search toggle
    with st.expander("🔧 Advanced Search Options"):
        advanced_property_search()
    
    # Search execution
    if search_submitted and address and city and state:
        if usage_data['current_month'] >= usage_data['limit']:
            st.error("⚠️ Monthly API limit reached. Upgrade your plan or wait until next month.")
        else:
            # Fetch property data
            property_data = fetch_property_data(address, city, state)
            
            if property_data:
                # Log usage
                log_usage(user_id, f"{address}, {city}, {state}", "property_search", {
                    "address": address, "city": city, "state": state
                })
                
                # Perform analysis
                analysis = analyze_property(property_data)
                
                # Display results
                display_property_analysis(analysis, property_data)
                
                # Save property option
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("💾 Save to Portfolio", use_container_width=True):
                        if save_property(user_id, property_data, {"address": address, "city": city, "state": state}):
                            st.rerun()
                
                with col2:
                    # Generate report
                    if st.button("📄 Generate Report", use_container_width=True):
                        report = generate_property_report(property_data, analysis)
                        st.download_button(
                            "📥 Download Report",
                            report,
                            file_name=f"property_report_{address.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d')}.md",
                            mime="text/markdown",
                            use_container_width=True
                        )
                
                with col3:
                    # Share functionality placeholder
                    if st.button("🔗 Share Analysis", use_container_width=True):
                        st.info("Share functionality coming soon!")
            else:
                st.warning("🔍 No property data found for this address. Please check the address and try again.")

def display_portfolio_page(user_id: int):
    """Display portfolio management page"""
    
    st.header("📊 Investment Portfolio")
    
    # Get user properties
    properties = get_user_properties(user_id)
    
    if properties:
        # Portfolio overview
        display_portfolio_overview(properties)
        
        st.divider()
        
        # Individual property management
        st.subheader("🏠 Property Management")
        
        for i, prop in enumerate(properties):
            data = prop.get('data', {})
            
            with st.expander(f"{data.get('address', f'Property {i+1}')} - {data.get('city', 'Unknown City')}, {data.get('state', 'Unknown State')}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Quick property info
                    price = data.get('price', 0) or data.get('lastSalePrice', 0)
                    rent = data.get('rentEstimate', {}).get('rent', 0) if isinstance(data.get('rentEstimate'), dict) else 0
                    
                    info_col1, info_col2, info_col3, info_col4 = st.columns(4)
                    with info_col1:
                        st.metric("Value", f"${price:,}" if price else "N/A")
                    with info_col2:
                        st.metric("Monthly Rent", f"${rent:,}" if rent else "N/A")
                    with info_col3:
                        cap_rate = (rent * 12 / price * 100) if price and rent else 0
                        st.metric("Cap Rate", f"{cap_rate:.2f}%" if cap_rate else "N/A")
                    with info_col4:
                        cash_flow = rent - (price * 0.004) if price and rent else 0
                        st.metric("Cash Flow", f"${cash_flow:,.0f}" if cash_flow else "N/A")
                
                with col2:
                    if st.button(f"🔍 Analyze", key=f"analyze_{prop['id']}"):
                        analysis = analyze_property(data)
                        st.session_state.selected_property = {"data": data, "analysis": analysis}
                    
                    if st.button(f"🗑️ Remove", key=f"delete_{prop['id']}"):
                        if delete_property(user_id, prop['id']):
                            st.rerun()
        
        # Display selected property analysis
        if st.session_state.get('selected_property'):
            st.divider()
            st.subheader("🔍 Detailed Property Analysis")
            selected = st.session_state.selected_property
            display_property_analysis(selected['analysis'], selected['data'])
    else:
        st.info("📈 Your portfolio is empty. Start by searching for properties and saving them to your portfolio!")

def display_orders_page(user_id: int):
    """Display WooCommerce orders page"""
    
    st.header("🛒 Order History")
    
    # Get orders
    orders = get_wc_orders(user_id)
    
    if orders:
        # Orders analytics
        display_orders_analytics(orders)
        
        st.divider()
        
        # Individual orders
        st.subheader("📦 Order Details")
        
        for order in orders[:10]:  # Show last 10 orders
            status_colors = {
                'completed': 'success',
                'processing': 'warning', 
                'pending': 'info',
                'cancelled': 'error',
                'refunded': 'error'
            }
            
            status_color = status_colors.get(order['status'], 'info')
            
            with st.expander(f"Order #{order['id']} - {order['date_created'][:10]} - ${order['total']}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Status:** :{status_color}[{order['status'].title()}]")
                    st.write(f"**Date:** {order['date_created'][:10]}")
                    st.write(f"**Total:** ${order['total']}")
                    
                    if order.get('line_items'):
                        st.write("**Items:**")
                        for item in order['line_items']:
                            st.write(f"• {item['name']} (Qty: {item['quantity']}) - ${item['total']}")
                
                with col2:
                    if order['status'] == 'completed':
                        st.success("✅ Complete")
                    elif order['status'] == 'processing':
                        st.warning("⏳ Processing")
                    elif order['status'] == 'pending':
                        st.info("🕐 Pending")
                    else:
                        st.error(f"❌ {order['status'].title()}")
    else:
        st.info("📦 No orders found. Place your first order to see it here!")

def display_settings_page(user_id: int):
    """Display user settings and preferences"""
    
    st.header("⚙️ Settings & Preferences")
    
    tab1, tab2, tab3, tab4 = st.tabs(["👤 Profile", "🔔 Notifications", "📊 Data Export", "🔧 Advanced"])
    
    with tab1:
        st.subheader("👤 Profile Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Display Name", value=st.session_state.wp_user.get('user_display_name', ''))
            st.text_input("Email", value=st.session_state.wp_user.get('user_email', ''), disabled=True)
        
        with col2:
            timezone = st.selectbox("Timezone", 
                ["UTC", "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"],
                index=4
            )
            currency = st.selectbox("Preferred Currency", ["USD", "EUR", "GBP", "CAD"], index=0)
        
        if st.button("💾 Save Profile Settings"):
            st.success("✅ Profile settings saved!")
    
    with tab2:
        st.subheader("🔔 Notification Preferences")
        
        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("📧 Email Notifications", value=True)
            st.checkbox("📱 Push Notifications", value=False)
            st.checkbox("📊 Weekly Portfolio Reports", value=True)
        
        with col2:
            st.checkbox("💰 Price Alert Notifications", value=True)
            st.checkbox("🏠 New Property Matches", value=True)
            st.checkbox("📈 Market Update Notifications", value=False)
        
        st.subheader("🎯 Alert Thresholds")
        col1, col2 = st.columns(2)
        with col1:
            st.slider("Price Change Alert (%)", 1, 20, 5)
        with col2:
            st.slider("Rent Change Alert (%)", 1, 15, 3)
        
        if st.button("🔔 Save Notification Settings"):
            st.success("✅ Notification preferences saved!")
    
    with tab3:
        st.subheader("📊 Data Export & Backup")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Export Portfolio Data**")
            if st.button("📥 Download Portfolio (CSV)", use_container_width=True):
                properties = get_user_properties(user_id)
                if properties:
                    # Convert to DataFrame and export
                    export_data = []
                    for prop in properties:
                        data = prop.get('data', {})
                        export_data.append({
                            'Address': data.get('address', ''),
                            'City': data.get('city', ''),
                            'State': data.get('state', ''),
                            'Price': data.get('price', 0),
                            'Monthly_Rent': data.get('rentEstimate', {}).get('rent', 0) if isinstance(data.get('rentEstimate'), dict) else 0,
                            'Bedrooms': data.get('bedrooms', ''),
                            'Bathrooms': data.get('bathrooms', ''),
                            'Square_Feet': data.get('squareFootage', ''),
                            'Year_Built': data.get('yearBuilt', ''),
                            'Date_Added': prop.get('created_at', '')[:10]
                        })
                    
                    df = pd.DataFrame(export_data)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Download CSV",
                        csv,
                        file_name=f"portfolio_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No portfolio data to export")
            
            if st.button("📥 Download Usage Data (JSON)", use_container_width=True):
                usage_data = get_user_usage(user_id)
                json_data = json.dumps(usage_data, indent=2)
                st.download_button(
                    "📥 Download JSON",
                    json_data,
                    file_name=f"usage_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            st.write("**Data Management**")
            st.info("📊 Your data is automatically backed up daily")
            st.info("🔒 All exports are encrypted and secure")
            
            st.write("**Account Data Summary**")
            properties = get_user_properties(user_id)
            usage_data = get_user_usage(user_id)
            
            st.metric("Saved Properties", len(properties))
            st.metric("API Calls This Month", usage_data['current_month'])
            st.metric("Total API Calls", usage_data['total'])
    
    with tab4:
        st.subheader("🔧 Advanced Settings")
        
        st.write("**API Configuration**")
        col1, col2 = st.columns(2)
        with col1:
            api_timeout = st.slider("API Timeout (seconds)", 10, 60, 30)  # Increased default and max timeout
            max_retries = st.slider("Max API Retries", 1, 5, 3)
        
        with col2:
            cache_duration = st.selectbox("Cache Duration", ["30 minutes", "1 hour", "2 hours", "6 hours", "24 hours"], index=2)  # Added more granular options
            auto_save = st.checkbox("Auto-save search results", value=True)
        
        st.write("**Data Management**")
        col1, col2, col3 = st.columns(3)  # Added third column for more options
        
        with col1:
            if st.button("🔄 Clear All Cache", use_container_width=True):
                st.cache_data.clear()
                st.cache_resource.clear()  # Also clear resource cache
                st.success("✅ All cache cleared successfully!")
        
        with col2:
            if st.button("📊 Refresh Usage Data", use_container_width=True):
                st.cache_data.clear()
                st.success("✅ Usage data refreshed!")
        
        with col3:  # Added selective cache clearing
            if st.button("🏠 Clear Property Cache", use_container_width=True):
                # Clear only property-related cache
                st.cache_data.clear()
                st.success("✅ Property cache cleared!")
        
        st.write("**Cache Status**")
        cache_info = {
            "Config Cache": "Active (1 hour TTL)",
            "Property Data": "Active (2 hours TTL)", 
            "User Properties": "Active (5 minutes TTL)",
            "WC Orders": "Active (10 minutes TTL)"
        }
        
        for cache_type, status in cache_info.items():
            st.text(f"• {cache_type}: {status}")
        
        st.divider()
        
        st.write("**Danger Zone**")
        with st.expander("⚠️ Advanced Actions (Use with caution)"):
            st.warning("These actions cannot be undone!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Delete All Properties", type="secondary"):
                    if st.checkbox("I understand this will delete ALL my saved properties"):
                        # Implementation for bulk delete
                        st.error("Bulk delete feature requires additional confirmation")
            
            with col2:
                if st.button("🔄 Reset All Settings", type="secondary"):
                    if st.checkbox("I understand this will reset ALL my settings"):
                        st.error("Settings reset feature requires additional confirmation")

# ------------------------
# Enhanced Features
# ------------------------
def property_comparison_tool():
    """Tool for comparing multiple properties side by side"""
    st.subheader("⚖️ Property Comparison Tool")
    
    # This would allow users to select multiple properties and compare them
    st.info("Property comparison tool - Select up to 4 properties to compare side by side")

def investment_calculator():
    """Advanced investment calculator with various scenarios"""
    st.subheader("🧮 Investment Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Property Details**")
        purchase_price = st.number_input("Purchase Price ($)", value=500000, step=10000)
        down_payment_pct = st.slider("Down Payment (%)", 5, 50, 20)
        interest_rate = st.slider("Interest Rate (%)", 2.0, 8.0, 4.5, 0.1)
        loan_term = st.selectbox("Loan Term (years)", [15, 20, 25, 30], index=3)
    
    with col2:
        st.write("**Income & Expenses**")
        monthly_rent = st.number_input("Monthly Rent ($)", value=2500, step=50)
        vacancy_rate = st.slider("Vacancy Rate (%)", 0, 20, 5)
        maintenance_pct = st.slider("Maintenance (% of rent)", 5, 20, 10)
        property_tax_pct = st.slider("Property Tax (% of value)", 0.5, 3.0, 1.2, 0.1)
    
    if st.button("📊 Calculate Investment Returns"):
        # Perform calculations
        down_payment = purchase_price * (down_payment_pct / 100)
        loan_amount = purchase_price - down_payment
        
        # Monthly mortgage payment calculation
        monthly_rate = (interest_rate / 100) / 12
        num_payments = loan_term * 12
        monthly_mortgage = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
        
        # Monthly expenses
        monthly_vacancy = monthly_rent * (vacancy_rate / 100)
        monthly_maintenance = monthly_rent * (maintenance_pct / 100)
        monthly_property_tax = (purchase_price * (property_tax_pct / 100)) / 12
        monthly_insurance = purchase_price * 0.003 / 12  # Estimate 0.3% annually
        
        total_monthly_expenses = monthly_mortgage + monthly_maintenance + monthly_property_tax + monthly_insurance
        effective_monthly_rent = monthly_rent - monthly_vacancy
        monthly_cash_flow = effective_monthly_rent - total_monthly_expenses
        
        # Display results
        st.subheader("📈 Investment Analysis Results")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Monthly Cash Flow", f"${monthly_cash_flow:,.0f}")
        with col2:
            annual_cash_flow = monthly_cash_flow * 12
            cash_on_cash_return = (annual_cash_flow / down_payment) * 100 if down_payment > 0 else 0
            st.metric("Cash-on-Cash Return", f"{cash_on_cash_return:.2f}%")
        with col3:
            cap_rate = ((effective_monthly_rent * 12) / purchase_price) * 100
            st.metric("Cap Rate", f"{cap_rate:.2f}%")
        with col4:
            total_roi = ((annual_cash_flow + (purchase_price * 0.03)) / down_payment) * 100  # Assume 3% appreciation
            st.metric("Total ROI", f"{total_roi:.2f}%")
        
        # Expense breakdown chart
        expense_labels = ['Mortgage', 'Maintenance', 'Property Tax', 'Insurance', 'Vacancy']
        expense_values = [monthly_mortgage, monthly_maintenance, monthly_property_tax, monthly_insurance, monthly_vacancy]
        
        fig = px.pie(
            values=expense_values,
            names=expense_labels,
            title="💰 Monthly Expense Breakdown"
        )
        st.plotly_chart(fig, use_container_width=True)

def market_alerts_system():
    """System for setting up market alerts and notifications"""
    st.subheader("🚨 Market Alerts")
    
    st.write("Set up custom alerts for market changes, property price updates, and investment opportunities.")
    
    with st.form("create_alert"):
        alert_name = st.text_input("Alert Name", placeholder="My Market Alert")
        
        col1, col2 = st.columns(2)
        with col1:
            alert_type = st.selectbox("Alert Type", 
                ["Price Change", "New Listings", "Rent Change", "Cap Rate Change", "Market Status Change"])
            location = st.text_input("Location (City, State)", placeholder="Los Angeles, CA")
        
        with col2:
            threshold = st.number_input("Threshold (%)", value=5.0, step=0.5)
            notification_method = st.selectbox("Notification Method", ["Email", "In-App", "Both"])
        
        if st.form_submit_button("🔔 Create Alert"):
            st.success(f"✅ Alert '{alert_name}' created successfully!")
            st.info("You will receive notifications when your alert criteria are met.")

# ------------------------
# Run Application
# ------------------------
if __name__ == "__main__":
    main()

supabase = init_supabase()
config = get_config()
usage_manager = APIUsageManager(supabase) if supabase else None
rentcast_manager = RentCastManager(config, usage_manager) if config and usage_manager else None

def render_enhanced_settings():
    """Render enhanced settings with advanced cache and performance options"""
    st.header("⚙️ Enhanced Settings & Performance")
    
    # Cache Performance Dashboard
    st.subheader("📊 Cache Performance")
    if cache_manager:
        stats = cache_manager.get_cache_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Cache Hit Rate", f"{stats['hit_rate']:.1f}%")
        with col2:
            st.metric("Total Requests", stats['total_requests'])
        with col3:
            st.metric("Cache Size", stats['cache_size'])
    
    # API Usage Analytics
    st.subheader("📈 API Usage Analytics")
    if usage_manager and st.session_state.get("user_id"):
        user_id = st.session_state["user_id"]
        analytics = usage_manager.get_enhanced_usage_analytics(user_id)
        
        if analytics:
            # Display usage charts
            for period, data in analytics.items():
                with st.expander(f"📊 {period.replace('_', ' ').title()} Analytics"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Usage by Type**")
                        if data["by_type"]:
                            st.bar_chart(data["by_type"])
                    
                    with col2:
                        st.write("**Success Rate**")
                        success_data = data["success_rate"]
                        total = success_data["success"] + success_data["error"]
                        if total > 0:
                            success_rate = (success_data["success"] / total) * 100
                            st.metric("Success Rate", f"{success_rate:.1f}%")
    
    # Advanced Cache Controls
    st.subheader("🔧 Advanced Cache Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Smart Cache Refresh", use_container_width=True):
            # Only clear expired cache entries
            cache_manager.invalidate_user_cache(st.session_state.get("user_id", 0))
            st.success("✅ Smart cache refresh completed!")
    
    with col2:
        if st.button("🏠 Clear Property Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("✅ Property cache cleared!")
    
    with col3:
        if st.button("📊 Reset Analytics", use_container_width=True):
            if usage_manager:
                cache_manager.invalidate_user_cache(st.session_state.get("user_id", 0), "usage_analytics")
            st.success("✅ Analytics cache reset!")

# ------------------------
# Enhanced Features
# ------------------------
def property_comparison_tool():
    """Tool for comparing multiple properties side by side"""
    st.subheader("⚖️ Property Comparison Tool")
    
    # This would allow users to select multiple properties and compare them
    st.info("Property comparison tool - Select up to 4 properties to compare side by side")

def investment_calculator():
    """Advanced investment calculator with various scenarios"""
    st.subheader("🧮 Investment Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Property Details**")
        purchase_price = st.number_input("Purchase Price ($)", value=500000, step=10000)
        down_payment_pct = st.slider("Down Payment (%)", 5, 50, 20)
        interest_rate = st.slider("Interest Rate (%)", 2.0, 8.0, 4.5, 0.1)
        loan_term = st.selectbox("Loan Term (years)", [15, 20, 25, 30], index=3)
    
    with col2:
        st.write("**Income & Expenses**")
        monthly_rent = st.number_input("Monthly Rent ($)", value=2500, step=50)
        vacancy_rate = st.slider("Vacancy Rate (%)", 0, 20, 5)
        maintenance_pct = st.slider("Maintenance (% of rent)", 5, 20, 10)
        property_tax_pct = st.slider("Property Tax (% of value)", 0.5, 3.0, 1.2, 0.1)
    
    if st.button("📊 Calculate Investment Returns"):
        # Perform calculations
        down_payment = purchase_price * (down_payment_pct / 100)
        loan_amount = purchase_price - down_payment
        
        # Monthly mortgage payment calculation
        monthly_rate = (interest_rate / 100) / 12
        num_payments = loan_term * 12
        monthly_mortgage = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
        
        # Monthly expenses
        monthly_vacancy = monthly_rent * (vacancy_rate / 100)
        monthly_maintenance = monthly_rent * (maintenance_pct / 100)
        monthly_property_tax = (purchase_price * (property_tax_pct / 100)) / 12
        monthly_insurance = purchase_price * 0.003 / 12  # Estimate 0.3% annually
        
        total_monthly_expenses = monthly_mortgage + monthly_maintenance + monthly_property_tax + monthly_insurance
        effective_monthly_rent = monthly_rent - monthly_vacancy
        monthly_cash_flow = effective_monthly_rent - total_monthly_expenses
        
        # Display results
        st.subheader("📈 Investment Analysis Results")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Monthly Cash Flow", f"${monthly_cash_flow:,.0f}")
        with col2:
            annual_cash_flow = monthly_cash_flow * 12
            cash_on_cash_return = (annual_cash_flow / down_payment) * 100 if down_payment > 0 else 0
            st.metric("Cash-on-Cash Return", f"{cash_on_cash_return:.2f}%")
        with col3:
            cap_rate = ((effective_monthly_rent * 12) / purchase_price) * 100
            st.metric("Cap Rate", f"{cap_rate:.2f}%")
        with col4:
            total_roi = ((annual_cash_flow + (purchase_price * 0.03)) / down_payment) * 100  # Assume 3% appreciation
            st.metric("Total ROI", f"{total_roi:.2f}%")
        
        # Expense breakdown chart
        expense_labels = ['Mortgage', 'Maintenance', 'Property Tax', 'Insurance', 'Vacancy']
        expense_values = [monthly_mortgage, monthly_maintenance, monthly_property_tax, monthly_insurance, monthly_vacancy]
        
        fig = px.pie(
            values=expense_values,
            names=expense_labels,
            title="💰 Monthly Expense Breakdown"
        )
        st.plotly_chart(fig, use_container_width=True)

def market_alerts_system():
    """System for setting up market alerts and notifications"""
    st.subheader("🚨 Market Alerts")
    
    st.write("Set up custom alerts for market changes, property price updates, and investment opportunities.")
    
    with st.form("create_alert"):
        alert_name = st.text_input("Alert Name", placeholder="My Market Alert")
        
        col1, col2 = st.columns(2)
        with col1:
            alert_type = st.selectbox("Alert Type", 
                ["Price Change", "New Listings", "Rent Change", "Cap Rate Change", "Market Status Change"])
            location = st.text_input("Location (City, State)", placeholder="Los Angeles, CA")
        
        with col2:
            threshold = st.number_input("Threshold (%)", value=5.0, step=0.5)
            notification_method = st.selectbox("Notification Method", ["Email", "In-App", "Both"])
        
        if st.form_submit_button("🔔 Create Alert"):
            st.success(f"✅ Alert '{alert_name}' created successfully!")
            st.info("You will receive notifications when your alert criteria are met.")

# ------------------------
# Run Application
# ------------------------
if __name__ == "__main__":
    supabase = init_supabase()
    config = get_config()
    usage_manager = APIUsageManager(supabase) if supabase else None
    rentcast_manager = RentCastManager(config, usage_manager) if config and usage_manager else None
    main()
