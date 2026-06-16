#!/usr/bin/env python3
"""
LinkedIn Content Generation Service Startup Script

This script helps users quickly start the LinkedIn content generation service
with proper configuration and validation.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_banner():
    """Print service banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  🚀 LinkedIn Content Generation Service                       ║
║                                                               ║
║  FastAPI-based AI content generation for LinkedIn            ║
║  Migrated from Streamlit to robust backend service           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)

def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'fastapi', 'uvicorn', 'pydantic', 'loguru', 
        'sqlalchemy', 'google-genai'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("💡 Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies installed!")
    return True

def check_environment():
    """Check environment configuration."""
    print("\n🔍 Checking environment configuration...")
    
    # Check API keys
    gemini_key = os.getenv('GEMINI_API_KEY')
    if not gemini_key:
        print("  ❌ GEMINI_API_KEY not set")
        print("     Set with: export GEMINI_API_KEY='your_api_key'")
        return False
    # elif not gemini_key.startswith('AIza'):
    #     print("  ⚠️  GEMINI_API_KEY format appears invalid (should start with 'AIza')")
        print("     Please verify your API key")
        return False
    else:
        print("  ✅ GEMINI_API_KEY configured")
    
    # Check database
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        print(f"  ✅ Database URL: {db_url}")
    else:
        print("  ✅ Database: Using Multi-tenant Workspace Architecture (dynamic paths)")
    
    # Check log level
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    print(f"  ✅ Log level: {log_level}")
    
    return True

def check_file_structure():
    """Check if all required files exist."""
    print("\n🔍 Checking file structure...")
    
    required_files = [
        'models/linkedin_models.py',
        'services/linkedin_service.py', 
        'routers/linkedin.py',
        'app.py'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️  Missing files: {', '.join(missing_files)}")
        return False
    
    return True

def validate_service():
    """Run structure validation."""
    print("\n🔍 Validating service structure...")
    
    try:
        result = subprocess.run(
            [sys.executable, 'validate_linkedin_structure.py'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("  ✅ Structure validation passed")
            return True
        else:
            print("  ❌ Structure validation failed")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("  ⚠️  Validation timeout")
        return False
    except Exception as e:
        print(f"  ❌ Validation error: {e}")
        return False

def start_server(host="0.0.0.0", port=8000, reload=True):
    """Start the FastAPI server."""
    print(f"\n🚀 Starting LinkedIn Content Generation Service...")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Reload: {reload}")
    print(f"   URL: http://localhost:{port}")
    print(f"   Docs: http://localhost:{port}/docs")
    print(f"   LinkedIn API: http://localhost:{port}/api/linkedin")
    
    try:
        cmd = [
            sys.executable, '-m', 'uvicorn', 
            'app:app',
            '--host', host,
            '--port', str(port)
        ]
        
        if reload:
            cmd.append('--reload')
        
        print(f"\n⚡ Executing: {' '.join(cmd)}")
        print("   Press Ctrl+C to stop the server")
        print("=" * 60)
        
        # Start the server
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

def print_usage_examples():
    """Print usage examples."""
    print("""
📚 Quick Start Examples:

1. Health Check:
   curl http://localhost:8000/api/linkedin/health

2. Generate LinkedIn Post:
   curl -X POST "http://localhost:8000/api/linkedin/generate-post" \\
     -H "Content-Type: application/json" \\
     -d '{
       "topic": "AI in Healthcare",
       "industry": "Healthcare",
       "tone": "professional",
       "include_hashtags": true,
       "research_enabled": true
     }'

3. Interactive Documentation:
   Open http://localhost:8000/docs in your browser

4. Available Endpoints:
   - POST /api/linkedin/generate-post
   - POST /api/linkedin/generate-article
   - POST /api/linkedin/generate-carousel
   - POST /api/linkedin/generate-video-script
   - POST /api/linkedin/generate-comment-response
   - GET  /api/linkedin/content-types
   - GET  /api/linkedin/usage-stats
    """)

def main():
    """Main startup function."""
    print_banner()
    
    # Check system requirements
    checks_passed = True
    
    if not check_dependencies():
        checks_passed = False
    
    if not check_environment():
        checks_passed = False
    
    if not check_file_structure():
        checks_passed = False
    
    if checks_passed and not validate_service():
        checks_passed = False
    
    if not checks_passed:
        print("\n❌ Pre-flight checks failed!")
        print("   Please resolve the issues above before starting the service.")
        sys.exit(1)
    
    print("\n✅ All pre-flight checks passed!")
    
    # Show usage examples
    print_usage_examples()
    
    # Ask user if they want to start the server
    try:
        response = input("\n🚀 Start the LinkedIn Content Generation Service? [Y/n]: ").strip().lower()
        if response in ['', 'y', 'yes']:
            start_server()
        else:
            print("👋 Service not started. Run 'uvicorn app:app --reload' when ready.")
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()