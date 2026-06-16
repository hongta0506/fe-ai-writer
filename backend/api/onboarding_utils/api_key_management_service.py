"""
API Key Management Service
Handles API key operations for onboarding.
"""

import time
from typing import Dict, Any
from fastapi import HTTPException
from loguru import logger

from services.onboarding.api_key_manager import APIKeyManager
from services.validation import check_all_api_keys

class APIKeyManagementService:
    """Service for handling API key management operations."""
    
    def __init__(self):
        # Initialize APIKeyManager with database support
        self.api_key_manager = APIKeyManager()
        # Ensure database service is available
        if not hasattr(self.api_key_manager, 'use_database'):
            self.api_key_manager.use_database = True
            # Legacy service removed - using direct DB access
            self.api_key_manager.db_service = None
        
        # Simple cache for API keys
        self._api_keys_cache = None
        self._cache_timestamp = 0
        self.CACHE_DURATION = 30  # Cache for 30 seconds
    
    async def get_api_keys(self) -> Dict[str, Any]:
        """Get all configured API keys (masked)."""
        current_time = time.time()
        
        # Return cached result if still valid
        if self._api_keys_cache and (current_time - self._cache_timestamp) < self.CACHE_DURATION:
            logger.debug("Returning cached API keys")
            return self._api_keys_cache
        
        try:
            self.api_key_manager.load_api_keys()  # Load keys from environment
            api_keys = self.api_key_manager.api_keys  # Get the loaded keys
            
            # Mask the API keys for security
            masked_keys = {}
            for provider, key in api_keys.items():
                if key:
                    masked_keys[provider] = "*" * (len(key) - 4) + key[-4:] if len(key) > 4 else "*" * len(key)
                else:
                    masked_keys[provider] = None
            
            result = {
                "api_keys": masked_keys,
                "total_providers": len(api_keys),
                "configured_providers": [k for k, v in api_keys.items() if v]
            }
            
            # Cache the result
            self._api_keys_cache = result
            self._cache_timestamp = current_time
            
            return result
        except Exception as e:
            logger.error(f"Error getting API keys: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_api_keys_for_onboarding(self, user_id: str | None = None) -> Dict[str, Any]:
        """Get all configured API keys for onboarding (unmasked), user-aware.

        In production, keys are per-user and stored in DB; in local, we use env.
        """
        try:
            # Prefer DB per-user keys when user_id is provided and DB is available
            if user_id and getattr(self.api_key_manager, 'use_database', False):
                try:
                    from services.database import SessionLocal
                    from models.onboarding import OnboardingSession, APIKey
                    
                    db = SessionLocal()
                    try:
                        # Find latest session for this user
                        session = db.query(OnboardingSession).filter(
                            OnboardingSession.user_id == user_id
                        ).order_by(OnboardingSession.updated_at.desc()).first()

                        if session:
                            rows = db.query(APIKey).filter(
                                APIKey.session_id == session.id
                            ).all()
                            # Columns: id, session_id, provider, key
                            api_keys = {r.provider: r.key for r in rows if r.key and r.provider}
                        
                        if api_keys:
                            logger.info(f"Loaded {len(api_keys)} API keys from database for user {user_id}")
                            return {
                                "api_keys": api_keys,
                                "total_providers": len(api_keys),
                                "configured_providers": [k for k, v in api_keys.items() if v]
                            }
                    finally:
                        db.close()
                except Exception as db_err:
                    logger.warning(f"DB lookup for API keys failed, falling back to env: {db_err}")

            # Fallback: load from environment/in-memory
            self.api_key_manager.load_api_keys()
            api_keys = self.api_key_manager.api_keys
            return {
                "api_keys": api_keys,
                "total_providers": len(api_keys),
                "configured_providers": [k for k, v in api_keys.items() if v]
            }
        except Exception as e:
            logger.error(f"Error getting API keys for onboarding: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def save_api_key(self, provider: str, api_key: str, description: str = None, current_user: dict = None) -> Dict[str, str]:
        """Save an API key for a provider.

        Persists to both in-memory/os.environ AND PostgreSQL ``api_keys`` table.
        """
        try:
            logger.info(f"📝 save_api_key called for provider: {provider}")

            # In-memory + os.environ (immediate availability)
            self.api_key_manager.save_api_key(provider, api_key)

            # Persist to PostgreSQL api_keys table
            user_id = current_user.get('id') or current_user.get('clerk_user_id') if current_user else None
            if user_id:
                self._persist_key_to_db(user_id, provider, api_key)
            else:
                logger.warning("No user_id — key saved to env only (not persisted to DB)")

            return {
                "message": f"API key for {provider} saved successfully",
                "provider": provider,
                "status": "saved"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error saving API key: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def _persist_key_to_db(self, user_id: str, provider: str, api_key: str) -> None:
        """Upsert API key into PostgreSQL api_keys table via onboarding_sessions FK."""
        try:
            from services.database import SessionLocal
            from models.onboarding import OnboardingSession, APIKey

            db = SessionLocal()
            try:
                session = db.query(OnboardingSession).filter(
                    OnboardingSession.user_id == user_id
                ).order_by(OnboardingSession.updated_at.desc()).first()

                if not session:
                    logger.warning(f"No onboarding session for user {user_id} — cannot persist API key {provider}")
                    return

                existing = db.query(APIKey).filter(
                    APIKey.session_id == session.id,
                    APIKey.provider == provider,
                ).first()

                if existing:
                    existing.key = api_key
                    existing.updated_at = __import__('datetime').datetime.utcnow()
                else:
                    db.add(APIKey(
                        session_id=session.id,
                        provider=provider,
                        key=api_key,
                    ))

                db.commit()
                logger.info(f"✅ DB: API key for {provider} persisted (user={user_id})")
            except Exception as db_err:
                logger.error(f"❌ DB persist failed for {provider}: {db_err}")
                db.rollback()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"❌ _persist_key_to_db error for {provider}: {e}")
    
    async def validate_api_keys(self) -> Dict[str, Any]:
        """Validate all configured API keys."""
        try:
            validation_results = check_all_api_keys(self.api_key_manager)
            
            return {
                "validation_results": validation_results.get('results', {}),
                "all_valid": validation_results.get('all_valid', False),
                "total_providers": len(validation_results.get('results', {}))
            }
        except Exception as e:
            logger.error(f"Error validating API keys: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
