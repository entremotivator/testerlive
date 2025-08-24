import streamlit as st
import pandas as pd
import requests
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from supabase import create_client, Client
import os
from functools import lru_cache
import logging
from dataclasses import dataclass
from enum import Enum
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import defaultdict, deque
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CACHE_TTL = {
    'config': 3600,  # 1 hour
    'property_data': 7200,  # 2 hours
    'user_data': 1800,  # 30 minutes
    'api_usage': 300,  # 5 minutes
    'market_data': 14400,  # 4 hours
}

class APIEndpoint(Enum):
    RENT_ESTIMATE = "rent-estimate"
    PROPERTY_DETAILS = "property-details"
    COMPARABLE_SALES = "comparable-sales"
    MARKET_ANALYSIS = "market-analysis"

@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.total_requests if self.total_requests > 0 else 0.0

class MemoryCache:
    """Enhanced memory cache with TTL and statistics"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
        self._stats = defaultdict(CacheStats)
        self._lock = threading.Lock()
    
    def get(self, key: str, category: str = "default") -> Optional[Any]:
        with self._lock:
            self._stats[category].total_requests += 1
            
            if key not in self._cache:
                self._stats[category].misses += 1
                return None
            
            # Check TTL
            ttl = CACHE_TTL.get(category, 3600)
            if time.time() - self._timestamps[key] > ttl:
                del self._cache[key]
                del self._timestamps[key]
                self._stats[category].misses += 1
                return None
            
            self._stats[category].hits += 1
            return self._cache[key]
    
    def set(self, key: str, value: Any, category: str = "default"):
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()
    
    def invalidate(self, pattern: str = None, category: str = None):
        with self._lock:
            if pattern:
                keys_to_remove = [k for k in self._cache.keys() if pattern in k]
                for key in keys_to_remove:
                    del self._cache[key]
                    del self._timestamps[key]
            elif category:
                # This is a simplified approach - in production, you'd want to track categories
                pass
    
    def get_stats(self) -> Dict[str, CacheStats]:
        return dict(self._stats)

# Global cache instance
memory_cache = MemoryCache()

@st.cache_data(ttl=CACHE_TTL['config'])
def get_config():
    """Get configuration with caching"""
    try:
        config = {
            'supabase_url': st.secrets.get("SUPABASE_URL", ""),
            'supabase_key': st.secrets.get("SUPABASE_ANON_KEY", ""),
            'rentcast_api_key': st.secrets.get("RENTCAST_API_KEY", ""),
            'wp_api_url': st.secrets.get("WP_API_URL", ""),
            'wp_api_key': st.secrets.get("WP_API_KEY", ""),
        }
        
        # Validate required config
        required_keys = ['supabase_url', 'supabase_key', 'rentcast_api_key']
        missing_keys = [key for key in required_keys if not config.get(key)]
        
        if missing_keys:
            st.error(f"Missing required configuration: {', '.join(missing_keys)}")
            return None
            
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        st.error("Failed to load configuration. Please check your secrets.")
        return None

@st.cache_resource
def init_supabase():
    """Initialize Supabase client with enhanced error handling and connection pooling"""
    cache_key = "supabase_client"
    cached_client = memory_cache.get(cache_key, "config")
    
    if cached_client:
        return cached_client
    
    try:
        config = get_config()
        if not config:
            return None
            
        # Enhanced client options for better performance
        client_options = {
            'auto_refresh_token': True,
            'persist_session': True,
            'detect_session_in_url': False,
            'headers': {
                'User-Agent': 'RealEstatePortal/1.0'
            }
        }
        
        supabase: Client = create_client(
            config['supabase_url'], 
            config['supabase_key'],
            options=client_options
        )
        
        # Test connection
        test_response = supabase.table('portal_users').select('id').limit(1).execute()
        
        memory_cache.set(cache_key, supabase, "config")
        logger.info("Supabase client initialized successfully")
        return supabase
        
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")
        st.error(f"Database connection failed: {str(e)}")
        return None

class EnhancedAPIUsageManager:
    """Enhanced API usage manager with comprehensive tracking and rate limiting"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.usage_cache = {}
        self.rate_limiter = defaultdict(deque)
        self.performance_metrics = defaultdict(list)
        
    def check_rate_limit(self, user_id: str, endpoint: str, limit_per_minute: int = 60) -> bool:
        """Check if user is within rate limits using sliding window"""
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        key = f"{user_id}_{endpoint}"
        
        # Clean old entries
        while self.rate_limiter[key] and self.rate_limiter[key][0] < window_start:
            self.rate_limiter[key].popleft()
        
        # Check if under limit
        if len(self.rate_limiter[key]) >= limit_per_minute:
            return False
        
        # Add current request
        self.rate_limiter[key].append(now)
        return True
    
    def track_api_call(self, user_id: str, endpoint: str, success: bool = True, 
                      response_time: float = 0, error_message: str = None):
        """Enhanced API call tracking with performance metrics"""
        try:
            # Performance tracking
            self.performance_metrics[f"{user_id}_{endpoint}"].append({
                'timestamp': time.time(),
                'response_time': response_time,
                'success': success
            })
            
            # Keep only last 100 entries per endpoint
            if len(self.performance_metrics[f"{user_id}_{endpoint}"]) > 100:
                self.performance_metrics[f"{user_id}_{endpoint}"] = \
                    self.performance_metrics[f"{user_id}_{endpoint}"][-100:]
            
            # Database tracking
            usage_data = {
                'user_id': user_id,
                'endpoint': endpoint,
                'timestamp': datetime.now().isoformat(),
                'success': success,
                'response_time_ms': int(response_time * 1000),
                'error_message': error_message,
                'date': datetime.now().date().isoformat(),
                'hour': datetime.now().hour
            }
            
            self.supabase.table('portal_api_usage').insert(usage_data).execute()
            
            # Invalidate cache
            cache_key = f"usage_{user_id}"
            memory_cache.invalidate(cache_key)
            
        except Exception as e:
            logger.error(f"Error tracking API call: {e}")
    
    def get_usage_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive usage analytics"""
        cache_key = f"usage_analytics_{user_id}"
        cached_data = memory_cache.get(cache_key, "api_usage")
        
        if cached_data:
            return cached_data
        
        try:
            now = datetime.now()
            
            # Get usage data for different time periods
            analytics = {}
            
            # Today's usage
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_usage = self.supabase.table('portal_api_usage')\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('timestamp', today_start.isoformat())\
                .execute()
            
            # This month's usage
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_usage = self.supabase.table('portal_api_usage')\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('timestamp', month_start.isoformat())\
                .execute()
            
            # Calculate analytics
            analytics = {
                'today': {
                    'total_calls': len(today_usage.data),
                    'successful_calls': len([r for r in today_usage.data if r['success']]),
                    'failed_calls': len([r for r in today_usage.data if not r['success']]),
                    'avg_response_time': np.mean([r['response_time_ms'] for r in today_usage.data]) if today_usage.data else 0,
                    'endpoints_used': len(set(r['endpoint'] for r in today_usage.data))
                },
                'month': {
                    'total_calls': len(month_usage.data),
                    'successful_calls': len([r for r in month_usage.data if r['success']]),
                    'failed_calls': len([r for r in month_usage.data if not r['success']]),
                    'avg_response_time': np.mean([r['response_time_ms'] for r in month_usage.data]) if month_usage.data else 0,
                    'endpoints_used': len(set(r['endpoint'] for r in month_usage.data)),
                    'daily_breakdown': self._get_daily_breakdown(month_usage.data),
                    'hourly_pattern': self._get_hourly_pattern(month_usage.data)
                }
            }
            
            # Success rates
            for period in ['today', 'month']:
                total = analytics[period]['total_calls']
                successful = analytics[period]['successful_calls']
                analytics[period]['success_rate'] = (successful / total * 100) if total > 0 else 100
            
            memory_cache.set(cache_key, analytics, "api_usage")
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting usage analytics: {e}")
            return {}
    
    def _get_daily_breakdown(self, usage_data: List[Dict]) -> Dict[str, int]:
        """Get daily breakdown of API usage"""
        daily_counts = defaultdict(int)
        for record in usage_data:
            date = record['date']
            daily_counts[date] += 1
        return dict(daily_counts)
    
    def _get_hourly_pattern(self, usage_data: List[Dict]) -> Dict[int, int]:
        """Get hourly usage pattern"""
        hourly_counts = defaultdict(int)
        for record in usage_data:
            hour = record['hour']
            hourly_counts[hour] += 1
        return dict(hourly_counts)

class EnhancedRentCastManager:
    """Enhanced RentCast API manager with intelligent retry logic and comprehensive error handling"""
    
    def __init__(self, config: Dict[str, str], usage_manager: EnhancedAPIUsageManager):
        self.api_key = config.get('rentcast_api_key')
        self.base_url = "https://api.rentcast.io/v1"
        self.usage_manager = usage_manager
        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'RealEstatePortal/1.0'
        })
        
        # Retry configuration
        self.max_retries = 3
        self.base_delay = 1.0
        self.max_delay = 60.0
        
    def _calculate_backoff_delay(self, attempt: int, base_delay: float = None) -> float:
        """Calculate exponential backoff delay with jitter"""
        if base_delay is None:
            base_delay = self.base_delay
            
        # Exponential backoff with jitter
        delay = min(base_delay * (2 ** attempt), self.max_delay)
        jitter = random.uniform(0.1, 0.3) * delay
        return delay + jitter
    
    def _make_request_with_retry(self, endpoint: str, params: Dict[str, Any], 
                                user_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Make API request with intelligent retry logic"""
        url = f"{self.base_url}/{endpoint}"
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            start_time = time.time()
            
            try:
                # Check rate limits
                if not self.usage_manager.check_rate_limit(user_id, endpoint):
                    return None, "Rate limit exceeded. Please try again later."
                
                response = self.session.get(url, params=params, timeout=30)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    self.usage_manager.track_api_call(
                        user_id, endpoint, True, response_time
                    )
                    return response.json(), None
                
                elif response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    if attempt < self.max_retries:
                        time.sleep(min(retry_after, self.max_delay))
                        continue
                    last_error = "API rate limit exceeded"
                
                elif response.status_code in [500, 502, 503, 504]:  # Server errors
                    if attempt < self.max_retries:
                        delay = self._calculate_backoff_delay(attempt)
                        time.sleep(delay)
                        continue
                    last_error = f"Server error: {response.status_code}"
                
                elif response.status_code == 401:
                    last_error = "Invalid API key"
                    break
                
                elif response.status_code == 404:
                    last_error = "Property not found"
                    break
                
                else:
                    last_error = f"API error: {response.status_code} - {response.text}"
                    break
                    
            except requests.exceptions.Timeout:
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                    continue
                last_error = "Request timeout"
                
            except requests.exceptions.ConnectionError:
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt, 2.0)
                    time.sleep(delay)
                    continue
                last_error = "Connection error"
                
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                break
        
        # Track failed request
        self.usage_manager.track_api_call(
            user_id, endpoint, False, time.time() - start_time, last_error
        )
        
        return None, last_error
    
    def get_property_details(self, address: str, user_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Get comprehensive property details with caching"""
        # Input validation
        if not address or len(address.strip()) < 5:
            return None, "Invalid address provided"
        
        address = address.strip()
        cache_key = f"property_details_{hashlib.md5(address.encode()).hexdigest()}"
        
        # Check cache first
        cached_data = memory_cache.get(cache_key, "property_data")
        if cached_data:
            return cached_data, None
        
        # Validate parameters
        params = {
            'address': address,
            'propertyType': 'Single Family',
            'bedrooms': '',
            'bathrooms': '',
            'squareFootage': ''
        }
        
        data, error = self._make_request_with_retry('properties', params, user_id)
        
        if data and not error:
            # Enrich data with additional calculations
            enriched_data = self._enrich_property_data(data)
            memory_cache.set(cache_key, enriched_data, "property_data")
            return enriched_data, None
        
        return None, error
    
    def get_rent_estimate(self, address: str, user_id: str, 
                         bedrooms: int = None, bathrooms: float = None, 
                         square_footage: int = None) -> Tuple[Optional[Dict], Optional[str]]:
        """Get rent estimate with enhanced parameters"""
        if not address or len(address.strip()) < 5:
            return None, "Invalid address provided"
        
        address = address.strip()
        cache_key = f"rent_estimate_{hashlib.md5(f'{address}_{bedrooms}_{bathrooms}_{square_footage}'.encode()).hexdigest()}"
        
        cached_data = memory_cache.get(cache_key, "property_data")
        if cached_data:
            return cached_data, None
        
        params = {
            'address': address,
            'propertyType': 'Single Family'
        }
        
        # Add optional parameters
        if bedrooms:
            params['bedrooms'] = str(bedrooms)
        if bathrooms:
            params['bathrooms'] = str(bathrooms)
        if square_footage:
            params['squareFootage'] = str(square_footage)
        
        data, error = self._make_request_with_retry('rent-estimate', params, user_id)
        
        if data and not error:
            # Add investment calculations
            enriched_data = self._add_investment_metrics(data, address)
            memory_cache.set(cache_key, enriched_data, "property_data")
            return enriched_data, None
        
        return None, error
    
    def get_comparable_sales(self, address: str, user_id: str, 
                           radius_miles: float = 0.5) -> Tuple[Optional[Dict], Optional[str]]:
        """Get comparable sales data"""
        if not address or len(address.strip()) < 5:
            return None, "Invalid address provided"
        
        address = address.strip()
        cache_key = f"comparable_sales_{hashlib.md5(f'{address}_{radius_miles}'.encode()).hexdigest()}"
        
        cached_data = memory_cache.get(cache_key, "property_data")
        if cached_data:
            return cached_data, None
        
        params = {
            'address': address,
            'radius': str(radius_miles),
            'count': '10'
        }
        
        data, error = self._make_request_with_retry('comparable-sales', params, user_id)
        
        if data and not error:
            memory_cache.set(cache_key, data, "property_data")
            return data, None
        
        return None, error
    
    def _enrich_property_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich property data with additional calculations"""
        try:
            enriched = data.copy()
            
            # Add market scoring
            enriched['market_score'] = self._calculate_market_score(data)
            
            # Add property condition assessment
            enriched['condition_assessment'] = self._assess_property_condition(data)
            
            # Add neighborhood insights
            enriched['neighborhood_insights'] = self._get_neighborhood_insights(data)
            
            return enriched
            
        except Exception as e:
            logger.error(f"Error enriching property data: {e}")
            return data
    
    def _add_investment_metrics(self, data: Dict[str, Any], address: str) -> Dict[str, Any]:
        """Add investment analysis metrics"""
        try:
            enriched = data.copy()
            
            if 'rent' in data and 'price' in data:
                monthly_rent = data['rent']
                property_price = data['price']
                
                if monthly_rent and property_price:
                    # Calculate key investment metrics
                    annual_rent = monthly_rent * 12
                    gross_yield = (annual_rent / property_price) * 100
                    
                    # Estimate expenses (typically 25-35% of rent)
                    estimated_expenses = monthly_rent * 0.30 * 12
                    net_annual_income = annual_rent - estimated_expenses
                    net_yield = (net_annual_income / property_price) * 100
                    
                    # Cash flow analysis (assuming 20% down, 6% interest)
                    down_payment = property_price * 0.20
                    loan_amount = property_price * 0.80
                    monthly_mortgage = loan_amount * 0.006  # Simplified calculation
                    
                    monthly_cash_flow = monthly_rent - monthly_mortgage - (estimated_expenses / 12)
                    
                    enriched['investment_metrics'] = {
                        'gross_yield_percent': round(gross_yield, 2),
                        'net_yield_percent': round(net_yield, 2),
                        'monthly_cash_flow': round(monthly_cash_flow, 2),
                        'annual_cash_flow': round(monthly_cash_flow * 12, 2),
                        'cap_rate_percent': round(net_yield, 2),
                        'down_payment_required': round(down_payment, 2),
                        'estimated_monthly_expenses': round(estimated_expenses / 12, 2)
                    }
            
            return enriched
            
        except Exception as e:
            logger.error(f"Error adding investment metrics: {e}")
            return data
    
    def _calculate_market_score(self, data: Dict[str, Any]) -> int:
        """Calculate a market attractiveness score (1-100)"""
        try:
            score = 50  # Base score
            
            # Price-to-rent ratio scoring
            if 'rent' in data and 'price' in data and data['rent'] and data['price']:
                price_to_rent_ratio = data['price'] / (data['rent'] * 12)
                if price_to_rent_ratio < 15:
                    score += 20
                elif price_to_rent_ratio < 20:
                    score += 10
                elif price_to_rent_ratio > 25:
                    score -= 10
            
            # Property age scoring
            if 'yearBuilt' in data and data['yearBuilt']:
                current_year = datetime.now().year
                age = current_year - data['yearBuilt']
                if age < 10:
                    score += 15
                elif age < 20:
                    score += 10
                elif age > 50:
                    score -= 10
            
            # Square footage scoring
            if 'squareFootage' in data and data['squareFootage']:
                sqft = data['squareFootage']
                if sqft > 2000:
                    score += 10
                elif sqft < 1000:
                    score -= 5
            
            return max(1, min(100, score))
            
        except Exception as e:
            logger.error(f"Error calculating market score: {e}")
            return 50
    
    def _assess_property_condition(self, data: Dict[str, Any]) -> str:
        """Assess property condition based on available data"""
        try:
            if 'yearBuilt' in data and data['yearBuilt']:
                current_year = datetime.now().year
                age = current_year - data['yearBuilt']
                
                if age < 5:
                    return "Excellent - New Construction"
                elif age < 15:
                    return "Very Good - Modern"
                elif age < 30:
                    return "Good - Well Maintained"
                elif age < 50:
                    return "Fair - May Need Updates"
                else:
                    return "Older - Likely Needs Renovation"
            
            return "Unknown - Insufficient Data"
            
        except Exception as e:
            logger.error(f"Error assessing property condition: {e}")
            return "Unknown - Error in Assessment"
    
    def _get_neighborhood_insights(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Generate neighborhood insights"""
        try:
            insights = {
                'walkability': 'Data not available',
                'school_district': 'Data not available',
                'crime_rate': 'Data not available',
                'appreciation_trend': 'Data not available'
            }
            
            # This would typically integrate with additional APIs
            # For now, return placeholder insights
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting neighborhood insights: {e}")
            return {}

def authenticate_wp_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user against WordPress with enhanced security"""
    cache_key = f"wp_auth_{hashlib.md5(f'{username}_{password}'.encode()).hexdigest()}"
    
    # Check cache first (short TTL for security)
    cached_user = memory_cache.get(cache_key, "user_data")
    if cached_user:
        return cached_user
    
    try:
        config = get_config()
        if not config or not config.get('wp_api_url'):
            # Fallback to Supabase authentication
            return authenticate_supabase_user(username, password)
        
        # WordPress API authentication
        wp_api_url = config['wp_api_url']
        auth_endpoint = f"{wp_api_url}/wp-json/custom/v1/authenticate"
        
        response = requests.post(
            auth_endpoint,
            json={'username': username, 'password': password},
            timeout=10,
            headers={'User-Agent': 'RealEstatePortal/1.0'}
        )
        
        if response.status_code == 200:
            user_data = response.json()
            if user_data.get('success'):
                wp_user = {
                    'id': user_data.get('user_id'),
                    'username': username,
                    'email': user_data.get('email', ''),
                    'display_name': user_data.get('display_name', username),
                    'roles': user_data.get('roles', []),
                    'auth_source': 'wordpress'
                }
                
                # Cache for 15 minutes
                memory_cache.set(cache_key, wp_user, "user_data")
                return wp_user
        
        return None
        
    except Exception as e:
        logger.error(f"WordPress authentication error: {e}")
        # Fallback to Supabase
        return authenticate_supabase_user(username, password)

def authenticate_supabase_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Fallback authentication using Supabase"""
    try:
        supabase = init_supabase()
        if not supabase:
            return None
        
        # Hash password for comparison (in production, use proper password hashing)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        result = supabase.table('wp_users')\
            .select('*')\
            .or_(f'user_login.eq.{username},user_email.eq.{username}')\
            .eq('user_pass', password_hash)\
            .execute()
        
        if result.data:
            user = result.data[0]
            return {
                'id': user['ID'],
                'username': user['user_login'],
                'email': user['user_email'],
                'display_name': user['display_name'],
                'roles': ['subscriber'],  # Default role
                'auth_source': 'supabase'
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Supabase authentication error: {e}")
        return None

def save_property_to_supabase(property_data: Dict[str, Any], user_id: str) -> bool:
    """Save property data to Supabase with enhanced error handling"""
    try:
        supabase = init_supabase()
        if not supabase:
            return False
        
        # Prepare property data for database
        db_property = {
            'user_id': user_id,
            'address': property_data.get('address', ''),
            'property_type': property_data.get('propertyType', 'Single Family'),
            'bedrooms': property_data.get('bedrooms'),
            'bathrooms': property_data.get('bathrooms'),
            'square_footage': property_data.get('squareFootage'),
            'year_built': property_data.get('yearBuilt'),
            'estimated_value': property_data.get('price'),
            'rent_estimate': property_data.get('rent'),
            'property_data': json.dumps(property_data),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Check if property already exists
        existing = supabase.table('portal_properties')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('address', db_property['address'])\
            .execute()
        
        if existing.data:
            # Update existing property
            result = supabase.table('portal_properties')\
                .update(db_property)\
                .eq('id', existing.data[0]['id'])\
                .execute()
        else:
            # Insert new property
            result = supabase.table('portal_properties')\
                .insert(db_property)\
                .execute()
        
        return len(result.data) > 0
        
    except Exception as e:
        logger.error(f"Error saving property to Supabase: {e}")
        return False

def get_user_properties(user_id: str) -> List[Dict[str, Any]]:
    """Get user's saved properties with caching"""
    cache_key = f"user_properties_{user_id}"
    cached_properties = memory_cache.get(cache_key, "user_data")
    
    if cached_properties:
        return cached_properties
    
    try:
        supabase = init_supabase()
        if not supabase:
            return []
        
        result = supabase.table('portal_properties')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .execute()
        
        properties = result.data or []
        
        # Parse JSON data
        for prop in properties:
            if prop.get('property_data'):
                try:
                    prop['parsed_data'] = json.loads(prop['property_data'])
                except json.JSONDecodeError:
                    prop['parsed_data'] = {}
        
        memory_cache.set(cache_key, properties, "user_data")
        return properties
        
    except Exception as e:
        logger.error(f"Error getting user properties: {e}")
        return []

def display_cache_performance():
    """Display cache performance metrics"""
    stats = memory_cache.get_stats()
    
    if not stats:
        st.info("No cache statistics available yet.")
        return
    
    st.subheader("🚀 Cache Performance")
    
    cols = st.columns(len(stats))
    
    for i, (category, stat) in enumerate(stats.items()):
        with cols[i]:
            st.metric(
                label=f"{category.title()} Cache",
                value=f"{stat.hit_rate:.1%}",
                delta=f"{stat.hits}/{stat.total_requests} hits"
            )

def display_usage_analytics(user_id: str, usage_manager: EnhancedAPIUsageManager):
    """Display comprehensive usage analytics"""
    analytics = usage_manager.get_usage_analytics(user_id)
    
    if not analytics:
        st.info("No usage data available yet.")
        return
    
    st.subheader("📊 API Usage Analytics")
    
    # Today's metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Today's Calls",
            analytics['today']['total_calls'],
            delta=f"{analytics['today']['successful_calls']} successful"
        )
    
    with col2:
        st.metric(
            "Success Rate",
            f"{analytics['today']['success_rate']:.1f}%"
        )
    
    with col3:
        st.metric(
            "Avg Response Time",
            f"{analytics['today']['avg_response_time']:.0f}ms"
        )
    
    with col4:
        st.metric(
            "Endpoints Used",
            analytics['today']['endpoints_used']
        )
    
    # Monthly trends
    if analytics['month']['daily_breakdown']:
        st.subheader("📈 Monthly Usage Trend")
        
        daily_data = analytics['month']['daily_breakdown']
        df = pd.DataFrame(list(daily_data.items()), columns=['Date', 'Calls'])
        df['Date'] = pd.to_datetime(df['Date'])
        
        fig = px.line(df, x='Date', y='Calls', title='Daily API Usage')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Hourly pattern
    if analytics['month']['hourly_pattern']:
        st.subheader("🕐 Usage Pattern by Hour")
        
        hourly_data = analytics['month']['hourly_pattern']
        df_hourly = pd.DataFrame(list(hourly_data.items()), columns=['Hour', 'Calls'])
        
        fig = px.bar(df_hourly, x='Hour', y='Calls', title='API Usage by Hour of Day')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

def display_property_analysis(property_data: Dict[str, Any]):
    """Display comprehensive property analysis"""
    st.subheader("🏠 Property Analysis")
    
    # Basic information
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Basic Information**")
        st.write(f"**Address:** {property_data.get('address', 'N/A')}")
        st.write(f"**Property Type:** {property_data.get('propertyType', 'N/A')}")
        st.write(f"**Bedrooms:** {property_data.get('bedrooms', 'N/A')}")
        st.write(f"**Bathrooms:** {property_data.get('bathrooms', 'N/A')}")
        st.write(f"**Square Footage:** {property_data.get('squareFootage', 'N/A'):,}" if property_data.get('squareFootage') else "**Square Footage:** N/A")
        st.write(f"**Year Built:** {property_data.get('yearBuilt', 'N/A')}")
    
    with col2:
        st.write("**Financial Information**")
        if property_data.get('price'):
            st.write(f"**Estimated Value:** ${property_data['price']:,}")
        if property_data.get('rent'):
            st.write(f"**Rent Estimate:** ${property_data['rent']:,}/month")
        
        # Market score
        if property_data.get('market_score'):
            score = property_data['market_score']
            color = "green" if score >= 70 else "orange" if score >= 50 else "red"
            st.markdown(f"**Market Score:** <span style='color: {color}'>{score}/100</span>", unsafe_allow_html=True)
        
        # Condition assessment
        if property_data.get('condition_assessment'):
            st.write(f"**Condition:** {property_data['condition_assessment']}")
    
    # Investment metrics
    if property_data.get('investment_metrics'):
        st.subheader("💰 Investment Analysis")
        
        metrics = property_data['investment_metrics']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Gross Yield", f"{metrics.get('gross_yield_percent', 0):.2f}%")
        
        with col2:
            st.metric("Net Yield", f"{metrics.get('net_yield_percent', 0):.2f}%")
        
        with col3:
            st.metric("Monthly Cash Flow", f"${metrics.get('monthly_cash_flow', 0):,.2f}")
        
        with col4:
            st.metric("Cap Rate", f"{metrics.get('cap_rate_percent', 0):.2f}%")
        
        # Additional investment details
        with st.expander("📋 Detailed Investment Breakdown"):
            st.write(f"**Down Payment Required (20%):** ${metrics.get('down_payment_required', 0):,.2f}")
            st.write(f"**Estimated Monthly Expenses:** ${metrics.get('estimated_monthly_expenses', 0):,.2f}")
            st.write(f"**Annual Cash Flow:** ${metrics.get('annual_cash_flow', 0):,.2f}")

def display_property_search():
    """Enhanced property search interface"""
    st.subheader("🔍 Property Search")
    
    # Search form
    with st.form("property_search_form", clear_on_submit=False):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            address = st.text_input(
                "Property Address",
                placeholder="Enter full address (e.g., 123 Main St, City, State ZIP)",
                help="Enter the complete address for best results"
            )
        
        with col2:
            search_type = st.selectbox(
                "Search Type",
                ["Property Details", "Rent Estimate", "Comparable Sales"],
                help="Choose the type of analysis you want"
            )
        
        # Advanced options
        with st.expander("🔧 Advanced Options"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                bedrooms = st.number_input("Bedrooms", min_value=0, max_value=10, value=None)
            
            with col2:
                bathrooms = st.number_input("Bathrooms", min_value=0.0, max_value=10.0, step=0.5, value=None)
            
            with col3:
                square_footage = st.number_input("Square Footage", min_value=0, value=None)
        
        search_button = st.form_submit_button("🔍 Search Property", use_container_width=True)
    
    if search_button and address:
        user_id = st.session_state.wp_user['id']
        
        with st.spinner(f"Searching for property information..."):
            if search_type == "Property Details":
                data, error = rentcast_manager.get_property_details(address, user_id)
            elif search_type == "Rent Estimate":
                data, error = rentcast_manager.get_rent_estimate(
                    address, user_id, bedrooms, bathrooms, square_footage
                )
            else:  # Comparable Sales
                data, error = rentcast_manager.get_comparable_sales(address, user_id)
            
            if error:
                st.error(f"❌ Error: {error}")
            elif data:
                st.success("✅ Property information retrieved successfully!")
                
                # Display results
                display_property_analysis(data)
                
                # Save option
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("💾 Save Property", use_container_width=True):
                        if save_property_to_supabase(data, user_id):
                            st.success("Property saved successfully!")
                            # Invalidate cache
                            memory_cache.invalidate(f"user_properties_{user_id}")
                        else:
                            st.error("Failed to save property.")
                
                with col2:
                    # Download data as JSON
                    json_data = json.dumps(data, indent=2)
                    st.download_button(
                        "📥 Download Data",
                        json_data,
                        file_name=f"property_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
            else:
                st.warning("⚠️ No data found for this property.")

def display_saved_properties():
    """Display user's saved properties with enhanced management"""
    st.subheader("🏠 Saved Properties")
    
    user_id = st.session_state.wp_user['id']
    properties = get_user_properties(user_id)
    
    if not properties:
        st.info("No saved properties yet. Search for properties to get started!")
        return
    
    # Property management options
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.write(f"**Total Properties:** {len(properties)}")
    
    with col2:
        if st.button("🔄 Refresh List"):
            memory_cache.invalidate(f"user_properties_{user_id}")
            st.rerun()
    
    with col3:
        view_mode = st.selectbox("View Mode", ["Cards", "Table"])
    
    if view_mode == "Cards":
        # Card view
        for i in range(0, len(properties), 2):
            cols = st.columns(2)
            
            for j, col in enumerate(cols):
                if i + j < len(properties):
                    prop = properties[i + j]
                    parsed_data = prop.get('parsed_data', {})
                    
                    with col:
                        with st.container():
                            st.markdown(f"**{prop.get('address', 'Unknown Address')}**")
                            
                            # Property details
                            details = []
                            if prop.get('bedrooms'):
                                details.append(f"{prop['bedrooms']} bed")
                            if prop.get('bathrooms'):
                                details.append(f"{prop['bathrooms']} bath")
                            if prop.get('square_footage'):
                                details.append(f"{prop['square_footage']:,} sqft")
                            
                            if details:
                                st.write(" • ".join(details))
                            
                            # Financial info
                            if prop.get('estimated_value'):
                                st.write(f"💰 **Value:** ${prop['estimated_value']:,}")
                            if prop.get('rent_estimate'):
                                st.write(f"🏠 **Rent:** ${prop['rent_estimate']:,}/month")
                            
                            # Market score
                            if parsed_data.get('market_score'):
                                score = parsed_data['market_score']
                                color = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔴"
                                st.write(f"{color} **Market Score:** {score}/100")
                            
                            st.write(f"📅 **Added:** {prop.get('created_at', '')[:10]}")
                            
                            # Action buttons
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button(f"👁️ View", key=f"view_{prop['id']}"):
                                    st.session_state[f"show_property_{prop['id']}"] = True
                            
                            with col_b:
                                if st.button(f"🗑️ Delete", key=f"delete_{prop['id']}"):
                                    # Delete property logic would go here
                                    st.warning("Delete functionality not implemented yet")
                            
                            st.markdown("---")
    
    else:
        # Table view
        table_data = []
        for prop in properties:
            parsed_data = prop.get('parsed_data', {})
            table_data.append({
                'Address': prop.get('address', 'N/A'),
                'Type': prop.get('property_type', 'N/A'),
                'Beds': prop.get('bedrooms', 'N/A'),
                'Baths': prop.get('bathrooms', 'N/A'),
                'Sqft': prop.get('square_footage', 'N/A'),
                'Value': f"${prop.get('estimated_value', 0):,}" if prop.get('estimated_value') else 'N/A',
                'Rent': f"${prop.get('rent_estimate', 0):,}" if prop.get('rent_estimate') else 'N/A',
                'Score': parsed_data.get('market_score', 'N/A'),
                'Added': prop.get('created_at', '')[:10]
            })
        
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)

def display_login_page():
    """Display the login page with WordPress authentication"""
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1 style='color: #2E86AB; margin-bottom: 0.5rem;'>🏠 Real Estate Portal</h1>
        <p style='color: #666; font-size: 1.1rem;'>Access your property dashboard</p>
    </div>
    """, unsafe_allow_html=True)
    
    import time
    form_key = f"login_form_{int(time.time() * 1000)}"
    
    with st.form(form_key):
        username = st.text_input("📧 WordPress Username/Email", placeholder="Enter your WordPress username or email")
        password = st.text_input("🔐 Password", type="password", placeholder="Enter your password")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_button = st.form_submit_button("🚀 Login", use_container_width=True)
        
        if login_button:
            if username and password:
                with st.spinner("🔐 Authenticating..."):
                    wp_user = authenticate_wp_user(username, password)
                    if wp_user:
                        st.session_state.wp_user = wp_user
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials. Please try again.")
            else:
                st.warning("⚠️ Please enter both username and password.")

def display_main_application():
    """Display the main application interface"""
    user = st.session_state.wp_user
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### Welcome, {user['display_name']}! 👋")
        st.markdown(f"**Email:** {user['email']}")
        st.markdown(f"**Auth Source:** {user['auth_source'].title()}")
        
        st.markdown("---")
        
        # Navigation
        page = st.selectbox(
            "📍 Navigate",
            ["🔍 Property Search", "🏠 Saved Properties", "📊 Usage Analytics", "🚀 Cache Performance", "⚙️ Settings"]
        )
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Main content
    if page == "🔍 Property Search":
        display_property_search()
    
    elif page == "🏠 Saved Properties":
        display_saved_properties()
    
    elif page == "📊 Usage Analytics":
        display_usage_analytics(user['id'], usage_manager)
    
    elif page == "🚀 Cache Performance":
        display_cache_performance()
    
    elif page == "⚙️ Settings":
        st.subheader("⚙️ Settings")
        st.info("Settings panel coming soon!")

def main():
    """Main application function"""
    st.set_page_config(
        page_title="Real Estate Portal",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    if 'wp_user' not in st.session_state:
        st.session_state.wp_user = None
    
    
    # Authentication check
    if st.session_state.wp_user is None:
        display_login_page()
    else:
        display_main_application()

# Initialize global components
if __name__ == "__main__":
    # Initialize configuration and managers
    config = get_config()
    supabase = init_supabase()
    usage_manager = EnhancedAPIUsageManager(supabase) if supabase else None
    rentcast_manager = EnhancedRentCastManager(config, usage_manager) if config and usage_manager else None
    
    # Run main application
    main()

