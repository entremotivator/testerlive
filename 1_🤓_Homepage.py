import streamlit as st
import requests
import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
import json
import time
from typing import Dict, List, Optional, Any
import hashlib
import uuid
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    .cache-status {
        position: fixed;
        top: 10px;
        right: 10px;
        background: rgba(0,0,0,0.7);
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 12px;
        z-index: 1000;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------
# Enhanced Supabase Client with Connection Management
# ------------------------
class SupabaseManager:
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client with error handling"""
        try:
            SUPABASE_URL = st.secrets["supabase"]["url"]
            SUPABASE_KEY = st.secrets["supabase"]["key"]
            self._client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")
            st.error(f"Failed to initialize Supabase: {e}")
            self._client = None
    
    @property
    def client(self) -> Optional[Client]:
        if self._client is None:
            self._initialize_client()
        return self._client
    
    def health_check(self) -> bool:
        """Check if Supabase connection is healthy"""
        try:
            if self._client:
                # Simple query to test connection
                result = self._client.table("user_sessions").select("count").limit(1).execute()
                return True
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            return False
        return False

# Global Supabase manager instance
supabase_manager = SupabaseManager()

# ------------------------
# Enhanced Configuration Management
# ------------------------
class ConfigManager:
    _config = None
    _last_loaded = None
    _cache_duration = 3600  # 1 hour
    
    @classmethod
    def get_config(cls) -> Optional[Dict]:
        """Get configuration with intelligent caching"""
        now = datetime.datetime.now()
        
        # Check if config needs refresh
        if (cls._config is None or 
            cls._last_loaded is None or 
            (now - cls._last_loaded).seconds > cls._cache_duration):
            
            cls._load_config()
        
        return cls._config
    
    @classmethod
    def _load_config(cls):
        """Load configuration from secrets"""
        try:
            cls._config = {
                "wp_url": st.secrets["wordpress"]["base_url"],
                "wp_user": st.secrets["wordpress"]["username"],
                "wp_pass": st.secrets["wordpress"]["password"],
                "wc_key": st.secrets["woocommerce"]["consumer_key"],
                "wc_secret": st.secrets["woocommerce"]["consumer_secret"],
                "rentcast_key": st.secrets["rentcast"]["api_key"],
                "rentcast_url": "https://api.rentcast.io/v1"
            }
            cls._last_loaded = datetime.datetime.now()
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Configuration error: {e}")
            st.error(f"Configuration error: {e}")
            cls._config = None

# ------------------------
# Enhanced Caching System using Supabase
# ------------------------
class SupabaseCache:
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.default_ttl = 3600  # 1 hour default
    
    def _generate_cache_key(self, key: str, user_id: Optional[int] = None, **kwargs) -> str:
        """Generate unique cache key with user context"""
        key_parts = [key]
        
        if user_id:
            key_parts.append(f"user_{user_id}")
        
        # Add additional parameters to key
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}_{v}")
        
        cache_key = "_".join(str(part).lower().replace(" ", "_") for part in key_parts)
        return hashlib.md5(cache_key.encode()).hexdigest()
    
    def get(self, key: str, user_id: Optional[int] = None, **kwargs) -> Optional[Any]:
        """Get cached data with expiration check"""
        try:
            cache_key = self._generate_cache_key(key, user_id, **kwargs)
            
            result = self.client.table("cache_data").select("*").eq(
                "cache_key", cache_key
            ).single().execute()
            
            if result.data:
                cached_item = result.data
                expires_at = datetime.datetime.fromisoformat(cached_item['expires_at'].replace('Z', '+00:00'))
                
                if datetime.datetime.now(datetime.timezone.utc) < expires_at:
                    logger.info(f"Cache hit for key: {key}")
                    return json.loads(cached_item['data'])
                else:
                    # Expired, delete it
                    self.delete(key, user_id, **kwargs)
                    logger.info(f"Cache expired for key: {key}")
            
            logger.info(f"Cache miss for key: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None, user_id: Optional[int] = None, **kwargs):
        """Set cached data with expiration"""
        try:
            cache_key = self._generate_cache_key(key, user_id, **kwargs)
            ttl = ttl or self.default_ttl
            expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=ttl)
            
            cache_data = {
                "cache_key": cache_key,
                "data": json.dumps(data, default=str),
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "user_id": user_id,
                "metadata": json.dumps(kwargs)
            }
            
            # Upsert cache data
            self.client.table("cache_data").upsert(cache_data).execute()
            logger.info(f"Cache set for key: {key}, TTL: {ttl}s")
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def delete(self, key: str, user_id: Optional[int] = None, **kwargs):
        """Delete cached data"""
        try:
            cache_key = self._generate_cache_key(key, user_id, **kwargs)
            self.client.table("cache_data").delete().eq("cache_key", cache_key).execute()
            logger.info(f"Cache deleted for key: {key}")
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
    
    def clear_user_cache(self, user_id: int):
        """Clear all cache for a specific user"""
        try:
            self.client.table("cache_data").delete().eq("user_id", user_id).execute()
            logger.info(f"User cache cleared for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Clear user cache error: {e}")
    
    def cleanup_expired(self):
        """Clean up expired cache entries"""
        try:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self.client.table("cache_data").delete().lt("expires_at", now).execute()
            logger.info("Expired cache entries cleaned up")
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")

# Initialize cache manager
cache = SupabaseCache(supabase_manager.client) if supabase_manager.client else None

# ------------------------
# Enhanced API Usage Tracking
# ------------------------
class APIUsageTracker:
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
    
    def check_rate_limit(self, user_id: int, endpoint: str = "default") -> Dict[str, Any]:
        """Check if user has exceeded rate limits BEFORE making API call"""
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Get current month usage
            result = self.client.table("api_usage").select("*").eq(
                "user_id", user_id
            ).eq("endpoint", endpoint).gte(
                "created_at", start_of_month.isoformat()
            ).execute()
            
            current_usage = len(result.data)
            
            # Get user's rate limit (default 100 per month)
            user_limit = self._get_user_limit(user_id)
            
            return {
                "allowed": current_usage < user_limit,
                "current_usage": current_usage,
                "limit": user_limit,
                "remaining": max(0, user_limit - current_usage),
                "reset_date": (start_of_month + datetime.timedelta(days=32)).replace(day=1)
            }
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return {"allowed": True, "current_usage": 0, "limit": 100, "remaining": 100}
    
    def _get_user_limit(self, user_id: int) -> int:
        """Get user's API rate limit based on their plan"""
        try:
            result = self.client.table("user_plans").select("api_limit").eq(
                "user_id", user_id
            ).single().execute()
            
            if result.data:
                return result.data.get("api_limit", 100)
        except:
            pass
        
        return 100  # Default limit
    
    def log_api_call(self, user_id: int, endpoint: str, query: str, 
                    success: bool, response_time: float, 
                    error_message: Optional[str] = None, 
                    metadata: Optional[Dict] = None):
        """Log API call with comprehensive metrics"""
        try:
            log_data = {
                "user_id": user_id,
                "endpoint": endpoint,
                "query": query,
                "success": success,
                "response_time_ms": int(response_time * 1000),
                "error_message": error_message,
                "metadata": json.dumps(metadata or {}),
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "ip_address": self._get_client_ip(),
                "user_agent": self._get_user_agent()
            }
            
            self.client.table("api_usage").insert(log_data).execute()
            logger.info(f"API call logged: {endpoint} - Success: {success}")
            
        except Exception as e:
            logger.error(f"API logging error: {e}")
    
    def _get_client_ip(self) -> str:
        """Get client IP address"""
        try:
            return st.session_state.get('client_ip', 'unknown')
        except:
            return 'unknown'
    
    def _get_user_agent(self) -> str:
        """Get user agent"""
        try:
            return st.session_state.get('user_agent', 'streamlit')
        except:
            return 'streamlit'
    
    def get_usage_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive usage analytics"""
        try:
            start_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
            
            result = self.client.table("api_usage").select("*").eq(
                "user_id", user_id
            ).gte("created_at", start_date.isoformat()).execute()
            
            usage_data = result.data
            
            # Calculate metrics
            total_calls = len(usage_data)
            successful_calls = len([u for u in usage_data if u['success']])
            failed_calls = total_calls - successful_calls
            
            # Response time metrics
            response_times = [u['response_time_ms'] for u in usage_data if u['response_time_ms']]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Endpoint breakdown
            endpoint_stats = {}
            for usage in usage_data:
                endpoint = usage['endpoint']
                if endpoint not in endpoint_stats:
                    endpoint_stats[endpoint] = {"count": 0, "success": 0, "failed": 0}
                
                endpoint_stats[endpoint]["count"] += 1
                if usage['success']:
                    endpoint_stats[endpoint]["success"] += 1
                else:
                    endpoint_stats[endpoint]["failed"] += 1
            
            # Daily usage pattern
            daily_usage = {}
            for usage in usage_data:
                date_key = usage['created_at'][:10]
                daily_usage[date_key] = daily_usage.get(date_key, 0) + 1
            
            return {
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "success_rate": (successful_calls / total_calls * 100) if total_calls > 0 else 0,
                "avg_response_time_ms": avg_response_time,
                "endpoint_stats": endpoint_stats,
                "daily_usage": daily_usage,
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Usage analytics error: {e}")
            return {}

# Initialize API usage tracker
api_tracker = APIUsageTracker(supabase_manager.client) if supabase_manager.client else None

# ------------------------
# Enhanced WordPress Integration with Token Management
# ------------------------
class WordPressManager:
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.config = ConfigManager.get_config()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Enhanced WordPress authentication with token management"""
        if not self.config:
            return None
        
        url = f"{self.config['wp_url']}/wp-json/jwt-auth/v1/token"
        
        try:
            start_time = time.time()
            
            with st.spinner("Authenticating with WordPress..."):
                resp = requests.post(
                    url,
                    data={"username": username, "password": password},
                    timeout=15
                )
            
            response_time = time.time() - start_time
            
            if resp.status_code == 200:
                token_data = resp.json()
                
                # Fetch detailed user information
                user_info = self._fetch_user_details(token_data['token'])
                if user_info:
                    token_data.update(user_info)
                
                # Store session with enhanced data
                self._store_user_session(token_data)
                
                # Log successful authentication
                if api_tracker:
                    api_tracker.log_api_call(
                        user_id=token_data.get('user_id', 0),
                        endpoint="wp_auth",
                        query=f"login_{username}",
                        success=True,
                        response_time=response_time,
                        metadata={"action": "login"}
                    )
                
                logger.info(f"User authenticated successfully: {username}")
                return token_data
            
            else:
                error_msg = resp.json().get('message', resp.text) if resp.text else 'Authentication failed'
                
                # Log failed authentication
                if api_tracker:
                    api_tracker.log_api_call(
                        user_id=0,
                        endpoint="wp_auth",
                        query=f"login_{username}",
                        success=False,
                        response_time=response_time,
                        error_message=error_msg
                    )
                
                st.error(f"🚫 Login failed: {error_msg}")
                return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"WordPress authentication error: {e}")
            st.error(f"🌐 Connection error: {e}")
            return None
    
    def _fetch_user_details(self, token: str) -> Optional[Dict]:
        """Fetch detailed user information from WordPress"""
        try:
            me_url = f"{self.config['wp_url']}/wp-json/wp/v2/users/me"
            resp = requests.get(
                me_url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            
            if resp.status_code == 200:
                user_info = resp.json()
                return {
                    "user_id": user_info.get("id"),
                    "user_email": user_info.get("email"),
                    "username": user_info.get("username"),
                    "display_name": user_info.get("name"),
                    "user_roles": user_info.get("roles", []),
                    "avatar_url": user_info.get("avatar_urls", {}).get("96", ""),
                    "user_registered": user_info.get("registered_date")
                }
        except Exception as e:
            logger.error(f"Failed to fetch user details: {e}")
        
        return None
    
    def _store_user_session(self, user_data: Dict):
        """Store enhanced user session data"""
        try:
            session_data = {
                "user_id": user_data["user_id"],
                "session_id": str(uuid.uuid4()),
                "token": user_data["token"],
                "token_expires": (datetime.datetime.now(datetime.timezone.utc) + 
                                datetime.timedelta(hours=24)).isoformat(),
                "last_login": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "user_data": json.dumps(user_data),
                "ip_address": api_tracker._get_client_ip() if api_tracker else "unknown",
                "user_agent": api_tracker._get_user_agent() if api_tracker else "streamlit",
                "is_active": True
            }
            
            # Deactivate old sessions
            self.client.table("user_sessions").update({"is_active": False}).eq(
                "user_id", user_data["user_id"]
            ).execute()
            
            # Insert new session
            self.client.table("user_sessions").insert(session_data).execute()
            
            logger.info(f"User session stored for user_id: {user_data['user_id']}")
            
        except Exception as e:
            logger.error(f"Failed to store user session: {e}")
    
    def refresh_token(self, user_id: int) -> Optional[str]:
        """Refresh JWT token for user"""
        try:
            # Get current session
            result = self.client.table("user_sessions").select("*").eq(
                "user_id", user_id
            ).eq("is_active", True).single().execute()
            
            if not result.data:
                return None
            
            session = result.data
            user_data = json.loads(session['user_data'])
            
            # Check if token needs refresh (refresh if expires in next hour)
            token_expires = datetime.datetime.fromisoformat(session['token_expires'].replace('Z', '+00:00'))
            if datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1) < token_expires:
                return session['token']  # Token still valid
            
            # Refresh token using WordPress API
            refresh_url = f"{self.config['wp_url']}/wp-json/jwt-auth/v1/token/validate"
            resp = requests.post(
                refresh_url,
                headers={"Authorization": f"Bearer {session['token']}"},
                timeout=10
            )
            
            if resp.status_code == 200:
                # Token is still valid, extend expiration
                new_expires = (datetime.datetime.now(datetime.timezone.utc) + 
                             datetime.timedelta(hours=24)).isoformat()
                
                self.client.table("user_sessions").update({
                    "token_expires": new_expires
                }).eq("user_id", user_id).eq("is_active", True).execute()
                
                return session['token']
            
            else:
                # Token expired, user needs to re-authenticate
                self.client.table("user_sessions").update({"is_active": False}).eq(
                    "user_id", user_id
                ).execute()
                return None
        
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
    
    def sync_user_data(self, user_id: int) -> bool:
        """Sync user data from WordPress to local cache"""
        try:
            # Get current session
            result = self.client.table("user_sessions").select("*").eq(
                "user_id", user_id
            ).eq("is_active", True).single().execute()
            
            if not result.data:
                return False
            
            token = result.data['token']
            
            # Fetch latest user data from WordPress
            user_info = self._fetch_user_details(token)
            if not user_info:
                return False
            
            # Update session with latest data
            self.client.table("user_sessions").update({
                "user_data": json.dumps(user_info),
                "last_sync": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }).eq("user_id", user_id).eq("is_active", True).execute()
            
            # Clear user-specific cache to force refresh
            if cache:
                cache.clear_user_cache(user_id)
            
            logger.info(f"User data synced for user_id: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"User data sync error: {e}")
            return False

# Initialize WordPress manager
wp_manager = WordPressManager(supabase_manager.client) if supabase_manager.client else None

# ------------------------
# Enhanced WooCommerce Integration with Caching
# ------------------------
def get_wc_orders_cached(user_id: int) -> List[Dict]:
    """Get WooCommerce orders with intelligent caching"""
    if not cache or not ConfigManager.get_config():
        return []
    
    # Check cache first
    cached_orders = cache.get("wc_orders", user_id=user_id)
    if cached_orders:
        return cached_orders
    
    # Fetch from API
    config = ConfigManager.get_config()
    url = f"{config['wp_url']}/wp-json/wc/v3/orders"
    params = {
        "customer": user_id,
        "per_page": 50,
        "orderby": "date",
        "order": "desc"
    }
    
    try:
        start_time = time.time()
        
        resp = requests.get(
            url,
            auth=(config['wc_key'], config['wc_secret']),
            params=params,
            timeout=15
        )
        
        response_time = time.time() - start_time
        
        if resp.status_code == 200:
            orders = resp.json()
            
            # Enrich order data
            for order in orders:
                order['total_float'] = float(order['total'])
                order['date_created_parsed'] = datetime.datetime.fromisoformat(
                    order['date_created'].replace('T', ' ').replace('Z', '')
                )
            
            # Cache for 10 minutes
            cache.set("wc_orders", orders, ttl=600, user_id=user_id)
            
            # Log API call
            if api_tracker:
                api_tracker.log_api_call(
                    user_id=user_id,
                    endpoint="wc_orders",
                    query=f"customer_{user_id}",
                    success=True,
                    response_time=response_time,
                    metadata={"order_count": len(orders)}
                )
            
            return orders
        
        else:
            error_msg = f"WooCommerce API error: {resp.text}"
            
            # Log failed API call
            if api_tracker:
                api_tracker.log_api_call(
                    user_id=user_id,
                    endpoint="wc_orders",
                    query=f"customer_{user_id}",
                    success=False,
                    response_time=response_time,
                    error_message=error_msg
                )
            
            st.error(error_msg)
            return []
    
    except requests.exceptions.RequestException as e:
        logger.error(f"WooCommerce API error: {e}")
        st.error(f"🌐 Failed to fetch orders: {e}")
        return []

# ------------------------
# Enhanced Property Data Fetching with Improved Caching
# ------------------------
def fetch_property_data_enhanced(address: str, city: str, state: str, user_id: int) -> Optional[Dict]:
    """Enhanced property data fetching with rate limiting and caching"""
    
    # Check rate limit BEFORE making API call
    if api_tracker:
        rate_limit_check = api_tracker.check_rate_limit(user_id, "rentcast_property")
        if not rate_limit_check["allowed"]:
            st.error(f"🚦 API rate limit exceeded. You have used {rate_limit_check['current_usage']}/{rate_limit_check['limit']} calls this month. Limit resets on {rate_limit_check['reset_date'].strftime('%B %d, %Y')}")
            return None
    
    # Check cache first
    if cache:
        cached_data = cache.get("property_data", user_id=user_id, 
                              address=address, city=city, state=state)
        if cached_data:
            st.info("📋 Using cached property data")
            return cached_data
    
    config = ConfigManager.get_config()
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
        "propertyType": "Single Family"
    }
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            
            with st.spinner(f"🔍 Fetching property data... (Attempt {attempt + 1}/{max_retries})"):
                resp = requests.get(url, headers=headers, params=params, timeout=30)
            
            response_time = time.time() - start_time
            
            if resp.status_code == 200:
                data = resp.json()
                
                if data and len(data) > 0:
                    property_data = data[0] if isinstance(data, list) else data
                    
                    # Enrich the data
                    property_data['fetch_timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    property_data['search_params'] = params
                    property_data['cache_key'] = f"{address}_{city}_{state}".lower().replace(" ", "_")
                    
                    # Cache for 2 hours
                    if cache:
                        cache.set("property_data", property_data, ttl=7200, 
                                user_id=user_id, address=address, city=city, state=state)
                    
                    # Log successful API call
                    if api_tracker:
                        api_tracker.log_api_call(
                            user_id=user_id,
                            endpoint="rentcast_property",
                            query=f"{address}, {city}, {state}",
                            success=True,
                            response_time=response_time,
                            metadata={"property_type": property_data.get("propertyType")}
                        )
                    
                    return property_data
                
                else:
                    st.warning("🔍 No property data found for this address")
                    
                    # Log API call with no results
                    if api_tracker:
                        api_tracker.log_api_call(
                            user_id=user_id,
                            endpoint="rentcast_property",
                            query=f"{address}, {city}, {state}",
                            success=True,
                            response_time=response_time,
                            metadata={"result": "no_data"}
                        )
                    
                    return None
            
            elif resp.status_code == 401:
                error_msg = "API Authentication failed - check your RentCast API key"
                st.error(f"🔑 {error_msg}")
                
                # Log authentication error
                if api_tracker:
                    api_tracker.log_api_call(
                        user_id=user_id,
                        endpoint="rentcast_property",
                        query=f"{address}, {city}, {state}",
                        success=False,
                        response_time=response_time,
                        error_message=error_msg
                    )
                
                return None
            
            elif resp.status_code == 429:
                if attempt < max_retries - 1:
                    st.warning(f"🚦 Rate limit hit, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    error_msg = "Rate limit exceeded - please wait before making another request"
                    st.error(f"🚦 {error_msg}")
                    
                    # Log rate limit error
                    if api_tracker:
                        api_tracker.log_api_call(
                            user_id=user_id,
                            endpoint="rentcast_property",
                            query=f"{address}, {city}, {state}",
                            success=False,
                            response_time=response_time,
                            error_message=error_msg
                        )
                    
                    return None
            
            elif resp.status_code >= 500:
                if attempt < max_retries - 1:
                    st.warning(f"🌐 Server error, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    error_msg = f"Server Error {resp.status_code}: {resp.text}"
                    st.error(f"🌐 {error_msg}")
                    
                    # Log server error
                    if api_tracker:
                        api_tracker.log_api_call(
                            user_id=user_id,
                            endpoint="rentcast_property",
                            query=f"{address}, {city}, {state}",
                            success=False,
                            response_time=response_time,
                            error_message=error_msg
                        )
                    
                    return None
            
            else:
                error_msg = f"API Error {resp.status_code}: {resp.text}"
                st.error(f"🌐 {error_msg}")
                
                # Log API error
                if api_tracker:
                    api_tracker.log_api_call(
                        user_id=user_id,
                        endpoint="rentcast_property",
                        query=f"{address}, {city}, {state}",
                        success=False,
                        response_time=response_time,
                        error_message=error_msg
                    )
                
                return None
        
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                st.warning(f"⏱️ Request timeout, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                error_msg = "Request timed out after multiple attempts"
                st.error(f"⏱️ {error_msg}")
                
                # Log timeout error
                if api_tracker:
                    api_tracker.log_api_call(
                        user_id=user_id,
                        endpoint="rentcast_property",
                        query=f"{address}, {city}, {state}",
                        success=False,
                        response_time=30.0,
                        error_message=error_msg
                    )
                
                return None
        
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                st.warning(f"🌐 Connection error, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                error_msg = f"Connection error: {e}"
                st.error(f"🌐 {error_msg}")
                
                # Log connection error
                if api_tracker:
                    api_tracker.log_api_call(
                        user_id=user_id,
                        endpoint="rentcast_property",
                        query=f"{address}, {city}, {state}",
                        success=False,
                        response_time=0.0,
                        error_message=error_msg
                    )
                
                return None
    
    return None

# ------------------------
# Enhanced Property Management with Better Caching
# ------------------------
def save_property_enhanced(user_id: int, data: Dict, search_params: Dict = None) -> bool:
    """Enhanced property saving with deduplication and caching"""
    if not supabase_manager.client:
        return False
    
    try:
        # Generate unique hash for deduplication
        property_hash = hashlib.md5(
            f"{data.get('address', '')}{data.get('city', '')}{data.get('state', '')}".encode()
        ).hexdigest()
        
        property_data = {
            "user_id": user_id,
            "property_hash": property_hash,
            "data": json.dumps(data),
            "search_params": json.dumps(search_params or {}),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "is_active": True
        }
        
        # Check if property already exists
        existing = supabase_manager.client.table("properties").select("id").eq(
            "user_id", user_id
        ).eq("property_hash", property_hash).execute()
        
        if existing.data:
            # Update existing
            supabase_manager.client.table("properties").update(property_data).eq(
                "id", existing.data[0]["id"]
            ).execute()
            st.success("🔄 Property updated successfully!")
        else:
            # Insert new
            supabase_manager.client.table("properties").insert(property_data).execute()
            st.success("💾 Property saved successfully!")
        
        # Clear user properties cache
        if cache:
            cache.delete("user_properties", user_id=user_id)
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to save property: {e}")
        st.error(f"Failed to save property: {e}")
        return False

def get_user_properties_cached(user_id: int, limit: int = 50, offset: int = 0) -> List[Dict]:
    """Get user properties with pagination and caching"""
    if not supabase_manager.client:
        return []
    
    # Check cache first
    if cache:
        cache_key = f"user_properties_limit_{limit}_offset_{offset}"
        cached_properties = cache.get(cache_key, user_id=user_id)
        if cached_properties:
            return cached_properties
    
    try:
        result = supabase_manager.client.table("properties").select("*").eq(
            "user_id", user_id
        ).eq("is_active", True).order(
            "updated_at", desc=True
        ).range(offset, offset + limit - 1).execute()
        
        properties = result.data
        
        # Parse JSON data
        for prop in properties:
            if isinstance(prop.get('data'), str):
                prop['data'] = json.loads(prop['data'])
            if isinstance(prop.get('search_params'), str):
                prop['search_params'] = json.loads(prop['search_params'])
        
        # Cache for 5 minutes
        if cache:
            cache_key = f"user_properties_limit_{limit}_offset_{offset}"
            cache.set(cache_key, properties, ttl=300, user_id=user_id)
        
        return properties
    
    except Exception as e:
        logger.error(f"Failed to fetch properties: {e}")
        st.error(f"Failed to fetch properties: {e}")
        return []

def delete_property_enhanced(user_id: int, property_id: int) -> bool:
    """Enhanced property deletion with cache invalidation"""
    if not supabase_manager.client:
        return False
    
    try:
        # Soft delete
        supabase_manager.client.table("properties").update({
            "is_active": False,
            "deleted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }).eq("id", property_id).eq("user_id", user_id).execute()
        
        # Clear user properties cache
        if cache:
            cache.clear_user_cache(user_id)
        
        st.success("🗑️ Property deleted successfully!")
        return True
    
    except Exception as e:
        logger.error(f"Failed to delete property: {e}")
        st.error(f"Failed to delete property: {e}")
        return False

# ------------------------
# Enhanced Rent Estimation with Caching
# ------------------------
def get_rent_estimate_cached(address: str, city: str, state: str, user_id: int) -> Dict:
    """Get rent estimate with caching and rate limiting"""
    
    # Check rate limit
    if api_tracker:
        rate_limit_check = api_tracker.check_rate_limit(user_id, "rentcast_rent")
        if not rate_limit_check["allowed"]:
            st.warning(f"🚦 Rent estimate API limit reached. {rate_limit_check['remaining']} calls remaining.")
            return {}
    
    # Check cache first
    if cache:
        cached_estimate = cache.get("rent_estimate", user_id=user_id,
                                  address=address, city=city, state=state)
        if cached_estimate:
            return cached_estimate
    
    config = ConfigManager.get_config()
    if not config:
        return {}
    
    url = f"{config['rentcast_url']}/rent-estimate"
    headers = {
        "accept": "application/json",
        "X-Api-Key": config['rentcast_key']
    }
    params = {
        "address": address,
        "city": city,
        "state": state
    }
    
    try:
        start_time = time.time()
        
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        response_time = time.time() - start_time
        
        if resp.status_code == 200:
            estimated_rent = resp.json()
            
            rent_data = {
                'monthly_rent': estimated_rent.get('rent', 0),
                'rent_range_low': estimated_rent.get('rentRangeLow', 0),
                'rent_range_high': estimated_rent.get('rentRangeHigh', 0),
                'confidence': estimated_rent.get('confidence', 'unknown'),
                'fetch_timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            
            # Cache for 4 hours
            if cache:
                cache.set("rent_estimate", rent_data, ttl=14400,
                        user_id=user_id, address=address, city=city, state=state)
            
            # Log successful API call
            if api_tracker:
                api_tracker.log_api_call(
                    user_id=user_id,
                    endpoint="rentcast_rent",
                    query=f"{address}, {city}, {state}",
                    success=True,
                    response_time=response_time,
                    metadata={"confidence": rent_data['confidence']}
                )
            
            return rent_data
        
        else:
            error_msg = f"Rent estimate API error: {resp.text}"
            
            # Log failed API call
            if api_tracker:
                api_tracker.log_api_call(
                    user_id=user_id,
                    endpoint="rentcast_rent",
                    query=f"{address}, {city}, {state}",
                    success=False,
                    response_time=response_time,
                    error_message=error_msg
                )
            
            st.warning(f"Failed to fetch rent estimates: {error_msg}")
            return {}
    
    except Exception as e:
        error_msg = f"Failed to fetch rent estimates: {e}"
        logger.error(error_msg)
        
        # Log exception
        if api_tracker:
            api_tracker.log_api_call(
                user_id=user_id,
                endpoint="rentcast_rent",
                query=f"{address}, {city}, {state}",
                success=False,
                response_time=0.0,
                error_message=error_msg
            )
        
        st.warning(error_msg)
        return {}

# ------------------------
# Property Analysis Functions (Enhanced)
# ------------------------
def analyze_property_enhanced(property_data: Dict, user_id: int) -> Dict:
    """Enhanced property analysis with caching"""
    
    # Check cache first
    if cache:
        property_hash = hashlib.md5(str(property_data).encode()).hexdigest()
        cached_analysis = cache.get("property_analysis", user_id=user_id, 
                                  property_hash=property_hash)
        if cached_analysis:
            return cached_analysis
    
    analysis = {
        'basic_info': extract_basic_info(property_data),
        'financial_metrics': calculate_financial_metrics(property_data),
        'market_analysis': perform_market_analysis(property_data),
        'investment_score': calculate_investment_score(property_data)
    }
    
    # Cache analysis for 1 hour
    if cache:
        property_hash = hashlib.md5(str(property_data).encode()).hexdigest()
        cache.set("property_analysis", analysis, ttl=3600,
                user_id=user_id, property_hash=property_hash)
    
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
            'roi_estimate': round((cash_flow * 12 / (price * 0.2)) * 100, 2) if price > 0 else 0
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
    return {
        'neighborhood': data.get('neighborhood', 'N/A'),
        'price_per_sqft': round(data.get('price', 0) / data.get('squareFootage', 1), 2) if data.get('squareFootage') else 0,
        'market_status': determine_market_status(data),
        'appreciation_potential': analyze_appreciation_potential(data)
    }

def determine_market_status(data: Dict) -> str:
    """Determine market status based on available data"""
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

# ------------------------
# Enhanced Display Functions
# ------------------------
def display_property_analysis_enhanced(analysis: Dict, property_data: Dict, user_id: int):
    """Display comprehensive property analysis with save option"""
    
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
    
    # Save Property Button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("💾 Save Property to Portfolio", use_container_width=True):
            search_params = {
                "address": basic['address'],
                "city": basic['city'],
                "state": basic['state']
            }
            if save_property_enhanced(user_id, property_data, search_params):
                st.balloons()
    
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
    create_property_charts_enhanced(financial, property_data)

def create_property_charts_enhanced(financial_data: Dict, property_data: Dict):
    """Create enhanced visualizations for property analysis"""
    
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
            financial_data['cap_rate'] * 10,
            min(financial_data['roi_estimate'], 100),
            max(0, min(100, (financial_data['estimated_cash_flow'] + 500) / 10)),
            max(0, min(100, 100 - financial_data['price_to_rent_ratio'] * 2))
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
# Enhanced Portfolio Management
# ------------------------
def display_portfolio_overview_enhanced(user_id: int):
    """Display enhanced portfolio analytics with pagination"""
    
    # Pagination controls
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page_size = st.selectbox("Properties per page", [10, 25, 50], index=1)
        page_number = st.number_input("Page", min_value=1, value=1)
    
    offset = (page_number - 1) * page_size
    properties = get_user_properties_cached(user_id, limit=page_size, offset=offset)
    
    if not properties:
        st.info("📊 No properties in your portfolio yet")
        return
    
    # Calculate portfolio metrics
    all_properties = get_user_properties_cached(user_id, limit=1000)  # Get all for metrics
    portfolio_metrics = calculate_portfolio_metrics_enhanced(all_properties)
    
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
    create_portfolio_charts_enhanced(all_properties, portfolio_metrics)
    
    # Property performance table
    display_portfolio_table_enhanced(properties, user_id)

def calculate_portfolio_metrics_enhanced(properties: List[Dict]) -> Dict:
    """Calculate enhanced portfolio metrics"""
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
            
            # Estimate cash flow
            monthly_expenses = price * 0.004
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

def create_portfolio_charts_enhanced(properties: List[Dict], metrics: Dict):
    """Create enhanced portfolio visualization charts"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Portfolio value distribution
        prop_values = []
        prop_labels = []
        
        for i, prop in enumerate(properties[:10]):  # Top 10 properties
            data = prop.get('data', {})
            price = data.get('price', 0) or data.get('lastSalePrice', 0)
            address = data.get('address', f'Property {i+1}')
            
            if price > 0:
                prop_values.append(price)
                prop_labels.append(address[:20] + '...' if len(address) > 20 else address)
        
        if prop_values:
            fig = px.pie(
                values=prop_values,
                names=prop_labels,
                title="🏠 Portfolio Value Distribution (Top 10)"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Cash flow by property
        cash_flows = []
        addresses = []
        
        for i, prop in enumerate(properties[:10]):
            data = prop.get('data', {})
            price = data.get('price', 0) or data.get('lastSalePrice', 0)
            rent = data.get('rentEstimate', {}).get('rent', 0) if isinstance(data.get('rentEstimate'), dict) else 0
            address = data.get('address', f'Property {i+1}')
            
            if price > 0:
                cash_flow = rent - (price * 0.004)
                cash_flows.append(cash_flow)
                addresses.append(address[:15] + '...' if len(address) > 15 else address)
        
        if cash_flows:
            fig = go.Figure(data=[
                go.Bar(
                    x=addresses,
                    y=cash_flows,
                    marker_color=['green' if cf > 0 else 'red' for cf in cash_flows]
                )
            ])
            fig.update_layout(
                title="💰 Monthly Cash Flow by Property",
                xaxis_title="Property",
                yaxis_title="Cash Flow ($)"
            )
            st.plotly_chart(fig, use_container_width=True)

def display_portfolio_table_enhanced(properties: List[Dict], user_id: int):
    """Display enhanced portfolio table with actions"""
    
    st.subheader("📋 Property Details")
    
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
            'ID': prop.get('id'),
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
        
        # Display table
        st.dataframe(filtered_df.drop('ID', axis=1), use_container_width=True)
        
        # Property actions
        st.subheader("🔧 Property Actions")
        selected_property = st.selectbox(
            "Select property for actions:",
            options=[(row['ID'], row['Property']) for _, row in filtered_df.iterrows()],
            format_func=lambda x: x[1]
        )
        
        if selected_property:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Refresh Data"):
                    # Clear cache for this property
                    if cache:
                        cache.clear_user_cache(user_id)
                    st.success("Property data cache cleared!")
                    st.rerun()
            
            with col2:
                if st.button("📊 View Analysis"):
                    # Find and display property analysis
                    prop_data = next((p for p in properties if p['id'] == selected_property[0]), None)
                    if prop_data:
                        analysis = analyze_property_enhanced(prop_data['data'], user_id)
                        display_property_analysis_enhanced(analysis, prop_data['data'], user_id)
            
            with col3:
                if st.button("🗑️ Delete Property", type="secondary"):
                    if delete_property_enhanced(user_id, selected_property[0]):
                        st.rerun()
        
        # Export option
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Portfolio Data (CSV)",
            data=csv,
            file_name=f"portfolio_data_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# ------------------------
# Enhanced Usage Analytics Display
# ------------------------
def display_usage_analytics(user_id: int):
    """Display comprehensive usage analytics"""
    if not api_tracker:
        st.error("API tracking not available")
        return
    
    st.subheader("📊 API Usage Analytics")
    
    # Time period selector
    col1, col2 = st.columns(2)
    with col1:
        days = st.selectbox("Analysis Period", [7, 30, 90], index=1)
    with col2:
        if st.button("🔄 Refresh Analytics"):
            if cache:
                cache.delete("usage_analytics", user_id=user_id)
            st.rerun()
    
    # Get analytics data
    analytics = api_tracker.get_usage_analytics(user_id, days)
    
    if not analytics:
        st.info("No usage data available")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total API Calls", analytics['total_calls'])
    with col2:
        st.metric("Success Rate", f"{analytics['success_rate']:.1f}%")
    with col3:
        st.metric("Avg Response Time", f"{analytics['avg_response_time_ms']:.0f}ms")
    with col4:
        st.metric("Failed Calls", analytics['failed_calls'])
    
    # Usage charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Daily usage pattern
        if analytics['daily_usage']:
            daily_df = pd.DataFrame(
                list(analytics['daily_usage'].items()),
                columns=['Date', 'Calls']
            )
            daily_df['Date'] = pd.to_datetime(daily_df['Date'])
            
            fig = px.line(
                daily_df,
                x='Date',
                y='Calls',
                title=f"📈 Daily API Usage ({days} days)"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Endpoint breakdown
        if analytics['endpoint_stats']:
            endpoint_data = []
            for endpoint, stats in analytics['endpoint_stats'].items():
                endpoint_data.append({
                    'Endpoint': endpoint,
                    'Total': stats['count'],
                    'Success': stats['success'],
                    'Failed': stats['failed']
                })
            
            endpoint_df = pd.DataFrame(endpoint_data)
            
            fig = px.bar(
                endpoint_df,
                x='Endpoint',
                y=['Success', 'Failed'],
                title="🎯 API Calls by Endpoint",
                barmode='stack'
            )
            st.plotly_chart(fig, use_container_width=True)

# ------------------------
# Enhanced Main Application
# ------------------------
def main():
    """Enhanced main application function"""
    
    # Initialize session state
    if "wp_user" not in st.session_state:
        st.session_state.wp_user = None
    
    if "selected_property" not in st.session_state:
        st.session_state.selected_property = None
    
    # Cache status indicator
    if cache and supabase_manager.health_check():
        st.markdown('<div class="cache-status">🟢 Cache Active</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="cache-status">🔴 Cache Offline</div>', unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏡 Real Estate Intelligence Portal</h1>
        <p>Enhanced with intelligent caching, API tracking, and WordPress sync</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Authentication check
    if st.session_state.wp_user is None:
        display_login_page_enhanced()
    else:
        display_main_application_enhanced()

def display_login_page_enhanced():
    """Display enhanced login interface"""
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h2 style="text-align: center; color: #333; margin-bottom: 2rem;">🔑 Enhanced Account Access</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("📧 WordPress Username/Email", placeholder="Enter your username or email")
            password = st.text_input("🔐 Password", type="password", placeholder="Enter your password")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                login_submitted = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if login_submitted and username and password:
                if wp_manager:
                    wp_user = wp_manager.authenticate_user(username, password)
                    if wp_user:
                        st.session_state.wp_user = wp_user
                        st.success("✅ Login successful! Redirecting...")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("WordPress manager not available")
        
        # System status
        st.markdown("### 🔧 System Status")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if supabase_manager.health_check():
                st.success("✅ Database")
            else:
                st.error("❌ Database")
        
        with col2:
            if cache:
                st.success("✅ Cache System")
            else:
                st.error("❌ Cache System")
        
        with col3:
            if ConfigManager.get_config():
                st.success("✅ Configuration")
            else:
                st.error("❌ Configuration")

def display_main_application_enhanced():
    """Display enhanced main application interface"""
    
    wp_user = st.session_state.wp_user
    user_id = wp_user["user_id"]
    
    # Auto-refresh token
    if wp_manager:
        refreshed_token = wp_manager.refresh_token(user_id)
        if not refreshed_token:
            st.warning("🔄 Session expired. Please log in again.")
            st.session_state.wp_user = None
            st.rerun()
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1rem; border-radius: 10px; color: white; margin-bottom: 1rem;">
            <h4 style="margin: 0;">👋 Welcome back!</h4>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">{wp_user.get('display_name', wp_user['user_email'])}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Enhanced usage tracking
        if api_tracker:
            rate_limit_info = api_tracker.check_rate_limit(user_id)
            usage_pct = (rate_limit_info['current_usage'] / rate_limit_info['limit']) * 100
            
            st.markdown("### 📊 API Usage This Month")
            st.progress(usage_pct / 100)
            st.write(f"{rate_limit_info['current_usage']}/{rate_limit_info['limit']} calls ({usage_pct:.1f}%)")
            st.write(f"🔄 Resets: {rate_limit_info['reset_date'].strftime('%B %d')}")
            
            # Quick analytics
            analytics = api_tracker.get_usage_analytics(user_id, 7)
            if analytics:
                st.write("**Last 7 days:**")
                st.write(f"• Success rate: {analytics['success_rate']:.1f}%")
                st.write(f"• Avg response: {analytics['avg_response_time_ms']:.0f}ms")
        
        st.divider()
        
        # Enhanced navigation
        page = st.selectbox(
            "🧭 Navigation",
            ["🏠 Property Search", "📊 Portfolio", "🛒 Orders", "📈 Analytics", "⚙️ Settings"]
        )
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        if st.button("🔄 Sync WordPress Data", use_container_width=True):
            if wp_manager and wp_manager.sync_user_data(user_id):
                st.success("✅ Data synced!")
            else:
                st.error("❌ Sync failed")
        
        if st.button("🧹 Clear My Cache", use_container_width=True):
            if cache:
                cache.clear_user_cache(user_id)
                st.success("✅ Cache cleared!")
            else:
                st.error("❌ Cache not available")
        
        st.divider()
        
        if st.button("🔓 Logout", use_container_width=True):
            st.session_state.wp_user = None
            st.rerun()
    
    # Main content area
    if page == "🏠 Property Search":
        display_property_search_enhanced(user_id)
    elif page == "📊 Portfolio":
        display_portfolio_overview_enhanced(user_id)
    elif page == "🛒 Orders":
        display_orders_page_enhanced(user_id)
    elif page == "📈 Analytics":
        display_usage_analytics(user_id)
    elif page == "⚙️ Settings":
        display_settings_page_enhanced(user_id)

def display_property_search_enhanced(user_id: int):
    """Display enhanced property search interface"""
    
    st.header("🔍 Enhanced Property Search & Analysis")
    
    # Rate limit check display
    if api_tracker:
        rate_limit_info = api_tracker.check_rate_limit(user_id, "rentcast_property")
        if rate_limit_info['remaining'] < 5:
            st.warning(f"⚠️ Only {rate_limit_info['remaining']} API calls remaining this month!")
    
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
    
    # Search execution
    if search_submitted and address and city and state:
        # Fetch property data with enhanced error handling
        property_data = fetch_property_data_enhanced(address, city, state, user_id)
        
        if property_data:
            # Perform enhanced analysis
            analysis = analyze_property_enhanced(property_data, user_id)
            
            # Display enhanced results
            display_property_analysis_enhanced(analysis, property_data, user_id)
            
            # Get rent estimate
            rent_estimate = get_rent_estimate_cached(address, city, state, user_id)
            if rent_estimate:
                st.subheader("🏠 Rent Estimate")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Monthly Rent", f"${rent_estimate['monthly_rent']:,.0f}")
                with col2:
                    st.metric("Range Low", f"${rent_estimate['rent_range_low']:,.0f}")
                with col3:
                    st.metric("Range High", f"${rent_estimate['rent_range_high']:,.0f}")
                with col4:
                    st.metric("Confidence", rent_estimate['confidence'].title())

def display_orders_page_enhanced(user_id: int):
    """Display enhanced orders page with caching"""
    
    st.header("🛒 Order Management")
    
    # Get cached orders
    orders = get_wc_orders_cached(user_id)
    
    if not orders:
        st.info("📦 No orders found")
        return
    
    # Enhanced order analytics
    display_orders_analytics_enhanced(orders)

def display_orders_analytics_enhanced(orders: List[Dict]):
    """Display enhanced order analytics"""
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
    
    # Enhanced order trend chart
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
            title="📈 Enhanced Order Trends Over Time",
            labels={'value': 'Count/Amount', 'month_str': 'Month'}
        )
        st.plotly_chart(fig, use_container_width=True)

def display_settings_page_enhanced(user_id: int):
    """Display enhanced settings page"""
    
    st.header("⚙️ Enhanced Settings")
    
    tab1, tab2, tab3, tab4 = st.tabs(["👤 Profile", "🔧 Preferences", "📊 Usage", "🔒 Security"])
    
    with tab1:
        st.subheader("👤 Profile Settings")
        
        # User info from WordPress
        wp_user = st.session_state.wp_user
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Display Name", value=wp_user.get('display_name', ''), disabled=True)
            st.text_input("Email", value=wp_user.get('user_email', ''), disabled=True)
        
        with col2:
            st.text_input("Username", value=wp_user.get('username', ''), disabled=True)
            st.text_input("User ID", value=str(wp_user.get('user_id', '')), disabled=True)
        
        if st.button("🔄 Sync Profile from WordPress"):
            if wp_manager and wp_manager.sync_user_data(user_id):
                st.success("✅ Profile synced successfully!")
                st.rerun()
    
    with tab2:
        st.subheader("🔧 Application Preferences")
        
        # Cache preferences
        st.markdown("**Cache Settings**")
        col1, col2 = st.columns(2)
        
        with col1:
            cache_duration = st.selectbox(
                "Default Cache Duration",
                [300, 600, 1800, 3600, 7200],
                index=3,
                format_func=lambda x: f"{x//60} minutes"
            )
        
        with col2:
            auto_refresh = st.checkbox("Auto-refresh expired data", value=True)
        
        # API preferences
        st.markdown("**API Settings**")
        col1, col2 = st.columns(2)
        
        with col1:
            max_retries = st.number_input("Max API Retries", min_value=1, max_value=5, value=3)
        
        with col2:
            timeout_seconds = st.number_input("Request Timeout (seconds)", min_value=10, max_value=60, value=30)
    
    with tab3:
        st.subheader("📊 Usage Statistics")
        display_usage_analytics(user_id)
    
    with tab4:
        st.subheader("🔒 Security Settings")
        
        # Session info
        st.markdown("**Current Session**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"**Login Time:** {wp_user.get('last_login', 'Unknown')}")
        
        with col2:
            st.info(f"**Session ID:** {wp_user.get('session_id', 'Unknown')[:8]}...")
        
        # Security actions
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Refresh Token", use_container_width=True):
                if wp_manager:
                    token = wp_manager.refresh_token(user_id)
                    if token:
                        st.success("✅ Token refreshed!")
                    else:
                        st.error("❌ Token refresh failed")
        
        with col2:
            if st.button("🧹 Clear All Data", use_container_width=True, type="secondary"):
                if cache:
                    cache.clear_user_cache(user_id)
                    st.success("✅ All user data cleared!")

# ------------------------
# Application Entry Point
# ------------------------
if __name__ == "__main__":
    # Cleanup expired cache on startup
    if cache:
        try:
            cache.cleanup_expired()
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
    
    # Run main application
    main()

