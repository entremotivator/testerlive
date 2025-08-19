"""
Configuration module for Real Estate Portal
Handles environment variables, API keys, and application settings
"""

import os
from typing import Dict, Any
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Real Estate Portal"""
    
    # Application Settings
    APP_NAME = "Real Estate Intelligence Portal"
    APP_VERSION = "2.0.0"
    DEBUG = os.getenv("DEBUG_MODE", "False").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    
    # WordPress Configuration
    WORDPRESS_URL = os.getenv("WORDPRESS_URL")
    WORDPRESS_JWT_SECRET = os.getenv("WORDPRESS_JWT_SECRET")
    
    # WooCommerce Configuration
    WOOCOMMERCE_CONSUMER_KEY = os.getenv("WOOCOMMERCE_CONSUMER_KEY")
    WOOCOMMERCE_CONSUMER_SECRET = os.getenv("WOOCOMMERCE_CONSUMER_SECRET")
    
    # RentCast API Configuration
    RENTCAST_API_KEY = os.getenv("RENTCAST_API_KEY")
    RENTCAST_BASE_URL = "https://api.rentcast.io/v1"
    
    # Optional API Keys
    ZILLOW_API_KEY = os.getenv("ZILLOW_API_KEY")
    REALTY_MOLE_API_KEY = os.getenv("REALTY_MOLE_API_KEY")
    
    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Redis Configuration
    REDIS_URL = os.getenv("REDIS_URL")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    
    # Email Configuration
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    
    # Security Configuration
    APP_SECRET_KEY = os.getenv("APP_SECRET_KEY")
    ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",")
    
    # API Rate Limiting
    API_RATE_LIMIT_PER_HOUR = int(os.getenv("API_RATE_LIMIT_PER_HOUR", "100"))
    API_RATE_LIMIT_PER_DAY = int(os.getenv("API_RATE_LIMIT_PER_DAY", "1000"))
    
    # File Upload Configuration
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    ALLOWED_FILE_TYPES = os.getenv("ALLOWED_FILE_TYPES", "csv,xlsx,pdf,jpg,png").split(",")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/app.log")
    
    # Cache Settings
    DEFAULT_CACHE_TTL = 3600  # 1 hour
    PROPERTY_CACHE_TTL = 1800  # 30 minutes
    USER_CACHE_TTL = 900  # 15 minutes
    
    # API Timeout Settings
    DEFAULT_API_TIMEOUT = 15
    MAX_API_RETRIES = 3
    
    # Pagination Settings
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

class StreamlitConfig:
    """Streamlit-specific configuration using st.secrets"""
    
    @staticmethod
    def get_supabase_config() -> Dict[str, str]:
        """Get Supabase configuration from Streamlit secrets"""
        try:
            return {
                "url": st.secrets["supabase"]["url"],
                "key": st.secrets["supabase"]["key"]
            }
        except KeyError as e:
            st.error(f"Missing Supabase configuration: {e}")
            return {}
    
    @staticmethod
    def get_wordpress_config() -> Dict[str, str]:
        """Get WordPress configuration from Streamlit secrets"""
        try:
            return {
                "url": st.secrets["wordpress"]["url"]
            }
        except KeyError as e:
            st.error(f"Missing WordPress configuration: {e}")
            return {}
    
    @staticmethod
    def get_woocommerce_config() -> Dict[str, str]:
        """Get WooCommerce configuration from Streamlit secrets"""
        try:
            return {
                "consumer_key": st.secrets["woocommerce"]["consumer_key"],
                "consumer_secret": st.secrets["woocommerce"]["consumer_secret"]
            }
        except KeyError as e:
            st.error(f"Missing WooCommerce configuration: {e}")
            return {}
    
    @staticmethod
    def get_rentcast_config() -> Dict[str, str]:
        """Get RentCast configuration from Streamlit secrets"""
        try:
            return {
                "api_key": st.secrets["rentcast"]["api_key"]
            }
        except KeyError as e:
            st.error(f"Missing RentCast configuration: {e}")
            return {}
    
    @staticmethod
    def get_database_config() -> Dict[str, Any]:
        """Get database configuration from Streamlit secrets"""
        try:
            return {
                "host": st.secrets.get("database", {}).get("host", "localhost"),
                "port": st.secrets.get("database", {}).get("port", 5432),
                "name": st.secrets.get("database", {}).get("name", "real_estate_portal"),
                "user": st.secrets.get("database", {}).get("user", "postgres"),
                "password": st.secrets.get("database", {}).get("password", "")
            }
        except KeyError:
            return {}
    
    @staticmethod
    def get_email_config() -> Dict[str, Any]:
        """Get email configuration from Streamlit secrets"""
        try:
            return {
                "smtp_server": st.secrets.get("email", {}).get("smtp_server", "smtp.gmail.com"),
                "smtp_port": st.secrets.get("email", {}).get("smtp_port", 587),
                "username": st.secrets.get("email", {}).get("username", ""),
                "password": st.secrets.get("email", {}).get("password", "")
            }
        except KeyError:
            return {}

class APIEndpoints:
    """API endpoint configurations"""
    
    # RentCast Endpoints
    RENTCAST_PROPERTIES = "/properties"
    RENTCAST_RENT_ESTIMATES = "/rent-estimates"
    RENTCAST_MARKET_DATA = "/market-data"
    RENTCAST_COMPARABLES = "/comparables"
    
    # WordPress Endpoints
    WP_JWT_TOKEN = "/wp-json/jwt-auth/v1/token"
    WP_JWT_VALIDATE = "/wp-json/jwt-auth/v1/token/validate"
    WP_USERS = "/wp-json/wp/v2/users"
    
    # WooCommerce Endpoints
    WC_ORDERS = "/wp-json/wc/v3/orders"
    WC_CUSTOMERS = "/wp-json/wc/v3/customers"
    WC_PRODUCTS = "/wp-json/wc/v3/products"

class DatabaseTables:
    """Database table names"""
    
    API_USAGE = "api_usage"
    PROPERTIES = "properties"
    USER_SESSIONS = "user_sessions"
    MARKET_ALERTS = "market_alerts"
    PROPERTY_COMPARISONS = "property_comparisons"
    USER_PREFERENCES = "user_preferences"
    PORTFOLIO_ANALYTICS = "portfolio_analytics"
    SAVED_SEARCHES = "saved_searches"

class CacheKeys:
    """Cache key prefixes"""
    
    USER_DATA = "user_data"
    PROPERTY_DATA = "property_data"
    MARKET_DATA = "market_data"
    API_USAGE = "api_usage"
    PORTFOLIO_ANALYTICS = "portfolio_analytics"

def validate_config() -> bool:
    """Validate that all required configuration is present"""
    required_configs = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "WORDPRESS_URL",
        "WOOCOMMERCE_CONSUMER_KEY",
        "WOOCOMMERCE_CONSUMER_SECRET",
        "RENTCAST_API_KEY"
    ]
    
    missing_configs = []
    
    # Check environment variables
    for config_name in required_configs:
        if not getattr(Config, config_name):
            missing_configs.append(config_name)
    
    # Check Streamlit secrets
    try:
        streamlit_configs = {
            "supabase": ["url", "key"],
            "wordpress": ["url"],
            "woocommerce": ["consumer_key", "consumer_secret"],
            "rentcast": ["api_key"]
        }
        
        for section, keys in streamlit_configs.items():
            if section in st.secrets:
                for key in keys:
                    if key not in st.secrets[section]:
                        missing_configs.append(f"{section}.{key}")
            else:
                missing_configs.extend([f"{section}.{key}" for key in keys])
                
    except Exception:
        # Streamlit secrets not available (likely running outside Streamlit)
        pass
    
    if missing_configs:
        print(f"Missing configuration: {', '.join(missing_configs)}")
        return False
    
    return True

def get_app_info() -> Dict[str, Any]:
    """Get application information"""
    return {
        "name": Config.APP_NAME,
        "version": Config.APP_VERSION,
        "environment": Config.ENVIRONMENT,
        "debug": Config.DEBUG
    }

# Export commonly used configurations
__all__ = [
    'Config',
    'StreamlitConfig',
    'APIEndpoints',
    'DatabaseTables',
    'CacheKeys',
    'validate_config',
    'get_app_info'
]
