from typing import Set
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from loguru import logger


_checked_subscription_plan_columns: bool = False
_checked_usage_summaries_columns: bool = False
_checked_api_usage_logs_columns: bool = False


def _get_table_columns(db: Session, table_name: str) -> Set[str]:
    """Return column names for SQLite/PostgreSQL/MySQL using SQLAlchemy inspector."""
    inspector = inspect(db.get_bind())
    return {col["name"] for col in inspector.get_columns(table_name)}


def ensure_subscription_plan_columns(db: Session) -> None:
    """Ensure required columns exist on subscription_plans for runtime safety.

    This is a defensive guard for environments where migrations have not yet
    been applied. If columns are missing (e.g., exa_calls_limit), we add them
    with a safe default so ORM queries do not fail.
    """
    global _checked_subscription_plan_columns
    if _checked_subscription_plan_columns:
        return

    try:
        # Discover existing columns using dialect-safe SQLAlchemy inspector
        cols: Set[str] = _get_table_columns(db, "subscription_plans")
        
        logger.debug(f"Schema check: Found {len(cols)} columns in subscription_plans table")

        # Columns we may reference in models but might be missing in older DBs
        required_columns = {
            "ai_text_generation_calls_limit": "INTEGER DEFAULT 0",
            "exa_calls_limit": "INTEGER DEFAULT 0",
            "video_calls_limit": "INTEGER DEFAULT 0",
            "image_edit_calls_limit": "INTEGER DEFAULT 0",
            "audio_calls_limit": "INTEGER DEFAULT 0",
            "wavespeed_calls_limit": "INTEGER DEFAULT 0",
        }

        for col_name, ddl in required_columns.items():
            if col_name not in cols:
                logger.info(f"Adding missing column {col_name} to subscription_plans table")
                try:
                    db.execute(text(f"ALTER TABLE subscription_plans ADD COLUMN {col_name} {ddl}"))
                    db.commit()
                    logger.info(f"Successfully added column {col_name}")
                except Exception as alter_err:
                    logger.error(f"Failed to add column {col_name}: {alter_err}")
                    db.rollback()
                    # Don't set flag on error - allow retry
                    raise
            else:
                logger.debug(f"Column {col_name} already exists")
        
        # Only set flag if we successfully completed the check
        _checked_subscription_plan_columns = True
    except Exception as e:
        logger.exception(f"Error ensuring subscription_plan columns: {e!r}")
        db.rollback()
        # Don't set the flag if there was an error, so we retry next time
        _checked_subscription_plan_columns = False
        raise


def ensure_usage_summaries_columns(db: Session) -> None:
    """Ensure required columns exist on usage_summaries for runtime safety.

    This is a defensive guard for environments where migrations have not yet
    been applied. If columns are missing (e.g., exa_calls, exa_cost), we add them
    with a safe default so ORM queries do not fail.
    """
    global _checked_usage_summaries_columns
    if _checked_usage_summaries_columns:
        return

    try:
        # Discover existing columns using dialect-safe SQLAlchemy inspector
        cols: Set[str] = _get_table_columns(db, "usage_summaries")
        
        logger.debug(f"Schema check: Found {len(cols)} columns in usage_summaries table")

        # Columns we may reference in models but might be missing in older DBs
        required_columns = {
            "exa_calls": "INTEGER DEFAULT 0",
            "exa_cost": "REAL DEFAULT 0.0",
            "video_calls": "INTEGER DEFAULT 0",
            "video_cost": "REAL DEFAULT 0.0",
            "image_edit_calls": "INTEGER DEFAULT 0",
            "image_edit_cost": "REAL DEFAULT 0.0",
            "audio_calls": "INTEGER DEFAULT 0",
            "audio_cost": "REAL DEFAULT 0.0",
            "wavespeed_calls": "INTEGER DEFAULT 0",
            "wavespeed_tokens": "INTEGER DEFAULT 0",
            "wavespeed_cost": "REAL DEFAULT 0.0",
        }

        for col_name, ddl in required_columns.items():
            if col_name not in cols:
                logger.info(f"Adding missing column {col_name} to usage_summaries table")
                try:
                    db.execute(text(f"ALTER TABLE usage_summaries ADD COLUMN {col_name} {ddl}"))
                    db.commit()
                    logger.info(f"Successfully added column {col_name}")
                except Exception as alter_err:
                    logger.error(f"Failed to add column {col_name}: {alter_err}")
                    db.rollback()
                    # Don't set flag on error - allow retry
                    raise
            else:
                logger.debug(f"Column {col_name} already exists")
        
        # Only set flag if we successfully completed the check
        _checked_usage_summaries_columns = True
    except Exception as e:
        logger.exception(f"Error ensuring usage_summaries columns: {e!r}")
        db.rollback()
        # Don't set the flag if there was an error, so we retry next time
        _checked_usage_summaries_columns = False
        raise


def ensure_api_usage_logs_columns(db: Session) -> None:
    """Ensure required columns exist on api_usage_logs for runtime safety.
    
    This is a defensive guard for environments where migrations have not yet
    been applied. If columns are missing (e.g., actual_provider_name), we add them
    with a safe default so ORM queries do not fail.
    """
    global _checked_api_usage_logs_columns
    if _checked_api_usage_logs_columns:
        return
    
    try:
        # Discover existing columns using dialect-safe SQLAlchemy inspector
        cols: Set[str] = _get_table_columns(db, "api_usage_logs")
        
        logger.debug(f"Schema check: Found {len(cols)} columns in api_usage_logs table")
        
        # Columns we may reference in models but might be missing in older DBs
        required_columns = {
            "actual_provider_name": "VARCHAR(50) NULL",
        }
        
        for col_name, ddl in required_columns.items():
            if col_name not in cols:
                logger.info(f"Adding missing column {col_name} to api_usage_logs table")
                try:
                    db.execute(text(f"ALTER TABLE api_usage_logs ADD COLUMN {col_name} {ddl}"))
                    db.commit()
                    logger.info(f"Successfully added column {col_name}")
                except Exception as alter_err:
                    logger.error(f"Failed to add column {col_name}: {alter_err}")
                    db.rollback()
                    # Don't set flag on error - allow retry
                    raise
            else:
                logger.debug(f"Column {col_name} already exists")
        
        # Only set flag if we successfully completed the check
        _checked_api_usage_logs_columns = True
    except Exception as e:
        logger.exception(f"Error ensuring api_usage_logs columns: {e!r}")
        db.rollback()
        # Don't set the flag if there was an error, so we retry next time
        _checked_api_usage_logs_columns = False
        raise


def ensure_all_schema_columns(db: Session) -> None:
    """Ensure all required columns exist in subscription-related tables."""
    ensure_subscription_plan_columns(db)
    ensure_usage_summaries_columns(db)
    ensure_api_usage_logs_columns(db)


