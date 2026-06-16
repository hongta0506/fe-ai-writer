"""
User API Key Context Manager
Provides user-specific API keys to backend services.

Resolution order (production & local):
  1. PostgreSQL via OnboardingDataIntegrationService
  2. os.environ (set by frontend's APIKeyManager.save_api_key during session)
  3. .env file (fallback)
"""

import os
from typing import Optional, Dict
from loguru import logger
from contextlib import contextmanager

class UserAPIKeyContext:
    """
    Context manager for user-specific API keys.
    
    Usage:
        with UserAPIKeyContext(user_id) as api_keys:
            gemini_key = api_keys.get('gemini')
            exa_key = api_keys.get('exa')
            # Use keys for this specific user
    """
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize with optional user_id.
        
        Args:
            user_id: User ID to fetch keys for. If None, uses .env keys (local mode)
        """
        self.user_id = user_id
        self.keys: Dict[str, str] = {}
        self._is_local = os.getenv('DEPLOY_ENV', 'local') == 'local'
    
    def __enter__(self):
        """Load API keys when entering context.

        Priority:
          1. PostgreSQL (OnboardingDataIntegrationService) when user_id provided
          2. os.environ (set at runtime by APIKeyManager during onboarding session)
          3. .env file (absolute fallback)
        """
        keys: Dict[str, str] = {}

        # Step 1: Try database (works in ALL environments when user_id available)
        if self.user_id:
            keys = self._load_from_database(self.user_id)
            if keys:
                logger.debug(f"[DB] Loaded {len(keys)} API keys from database for user {self.user_id}")
                self.keys = keys
                return self.keys

        # Step 2: os.environ (set by frontend's APIKeyManager during active session)
        env_keys = self._load_from_env()
        if any(env_keys.values()):
            logger.debug(f"[ENV] Loaded {sum(1 for v in env_keys.values() if v)} API keys from environment")
            keys = env_keys

        # Step 3: .env file (fallback)
        if not any(keys.values()):
            from dotenv import load_dotenv
            from pathlib import Path
            backend_dir = Path(__file__).resolve().parent.parent
            env_path = backend_dir / '.env'
            if env_path.exists():
                load_dotenv(env_path, override=True)
                keys = self._load_from_env()
                logger.debug(f"[DOTENV] Loaded {sum(1 for v in keys.values() if v)} API keys from .env file")

        self.keys = keys
        return self.keys
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting context."""
        self.keys.clear()
        return False  # Don't suppress exceptions
    
    def _load_from_env(self) -> Dict[str, str]:
        """Load API keys from environment variables (.env file)."""
        return {
            'gemini': os.getenv('GEMINI_API_KEY', ''),
            'exa': os.getenv('EXA_API_KEY', ''),
            'copilotkit': os.getenv('COPILOTKIT_API_KEY', ''),
            'openai': os.getenv('OPENAI_API_KEY', ''),
            'anthropic': os.getenv('ANTHROPIC_API_KEY', ''),
            'tavily': os.getenv('TAVILY_API_KEY', ''),
            'serper': os.getenv('SERPER_API_KEY', ''),
            'firecrawl': os.getenv('FIRECRAWL_API_KEY', ''),
        }
    
    def _load_from_database(self, user_id: str) -> Dict[str, str]:
        """Load API keys from database for specific user.

        Reads from ``api_keys`` table via ``onboarding_sessions.user_id`` join.
        Columns: id, session_id, provider, key, created_at, updated_at.
        """
        try:
            from services.database import get_session_for_user
            from models.onboarding import OnboardingSession, APIKey

            db = get_session_for_user(user_id)
            if not db:
                logger.error(f"Failed to create DB session for user {user_id}")
                return {}
            try:
                # Find the latest onboarding session for this user
                session = db.query(OnboardingSession).filter(
                    OnboardingSession.user_id == user_id
                ).order_by(OnboardingSession.updated_at.desc()).first()

                if not session:
                    logger.info(f"No onboarding session for user {user_id}")
                    return {}

                # Query api_keys via session_id (actual schema: session_id, provider, key)
                rows = db.query(APIKey).filter(
                    APIKey.session_id == session.id
                ).all()

                keys: Dict[str, str] = {}
                for row in rows:
                    if row.key and row.provider:
                        keys[row.provider.lower()] = row.key

                if keys:
                    logger.info(
                        f"[DB] Loaded {len(keys)} API keys from database "
                        f"for user {user_id} (providers: {list(keys.keys())})"
                    )
                else:
                    logger.info(f"No API keys in DB for user {user_id}")

                return keys
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to load API keys from database for user {user_id}: {e}")
            return {}
    
    @staticmethod
    def get_user_key(user_id: Optional[str], provider: str) -> Optional[str]:
        """
        Convenience method to get a single API key for a user.
        
        Args:
            user_id: User ID (None for development mode)
            provider: Provider name (e.g., 'gemini', 'exa')
            
        Returns:
            API key string or None
        """
        with UserAPIKeyContext(user_id) as keys:
            return keys.get(provider)


@contextmanager
def user_api_keys(user_id: Optional[str] = None):
    """
    Context manager function for easier usage.
    
    Usage:
        from services.user_api_key_context import user_api_keys
        
        with user_api_keys(user_id) as keys:
            gemini_key = keys.get('gemini')
    """
    context = UserAPIKeyContext(user_id)
    try:
        yield context.__enter__()
    finally:
        context.__exit__(None, None, None)


# Convenience function for FastAPI dependency injection
def get_user_api_keys(user_id: str) -> Dict[str, str]:
    """
    Get user-specific API keys for use in FastAPI endpoints.
    
    Args:
        user_id: User ID from current_user
        
    Returns:
        Dictionary of API keys for this user
    """
    with UserAPIKeyContext(user_id) as keys:
        return keys


def get_gemini_key(user_id: Optional[str] = None) -> Optional[str]:
    """Get Gemini API key for user."""
    return UserAPIKeyContext.get_user_key(user_id, 'gemini')


def get_exa_key(user_id: Optional[str] = None) -> Optional[str]:
    """Get Exa API key for user."""
    return UserAPIKeyContext.get_user_key(user_id, 'exa')


def get_tavily_key(user_id: Optional[str] = None) -> Optional[str]:
    """Get Tavily API key for user."""
    return UserAPIKeyContext.get_user_key(user_id, 'tavily')


def get_copilotkit_key(user_id: Optional[str] = None) -> Optional[str]:
    """Get CopilotKit API key for user."""
    return UserAPIKeyContext.get_user_key(user_id, 'copilotkit')
