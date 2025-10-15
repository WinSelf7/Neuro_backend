#!/usr/bin/env python3
"""
Database initialization script
Run this script to create database tables
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    """Initialize database tables"""
    from database import init_db
    from loguru import logger
    
    logger.info("Starting database initialization...")
    
    try:
        await init_db()
        logger.info("✅ Database initialized successfully!")
        logger.info("All tables have been created.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

