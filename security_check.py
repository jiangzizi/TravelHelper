#!/usr/bin/env python3
"""
Security validation script for TravelHelper
Run this to check for security vulnerabilities
"""

import os
import sys
import re
import subprocess
from pathlib import Path

def check_hardcoded_secrets():
    """Check for hardcoded secrets in code"""
    print("🔍 Checking for hardcoded secrets...")
    
    # Patterns that indicate hardcoded secrets
    secret_patterns = [
        r'password\s*=\s*["\'][^"\']+["\']',
        r'secret_key\s*=\s*["\'][^"\']+["\']',
        r'api_key\s*=\s*["\'][^"\']+["\']',
        r'token\s*=\s*["\'][^"\']+["\']'
    ]
    
    python_files = Path('.').glob('**/*.py')
    issues = []
    
    for file_path in python_files:
        if 'migrations' in str(file_path) or '__pycache__' in str(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for i, line in enumerate(content.split('\n'), 1):
                for pattern in secret_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Skip if it uses environment variables
                        if 'os.getenv' in line or 'os.environ' in line:
                            continue
                        issues.append(f"{file_path}:{i} - {line.strip()}")
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
    
    if issues:
        print("❌ Found potential hardcoded secrets:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("✅ No hardcoded secrets found")
        return True

def check_debug_settings():
    """Check if debug is disabled in production"""
    print("\n🔍 Checking debug settings...")
    
    settings_file = Path('TravelHelper/settings.py')
    if not settings_file.exists():
        print("❌ Settings file not found")
        return False
    
    with open(settings_file, 'r') as f:
        content = f.read()
    
    # Check if DEBUG uses environment variable
    if 'DEBUG = os.getenv' in content or "DEBUG = False" in content:
        print("✅ DEBUG properly configured with environment variable")
        return True
    elif 'DEBUG = True' in content:
        print("❌ DEBUG is hardcoded to True")
        return False
    else:
        print("⚠️  DEBUG configuration unclear")
        return False

def check_csrf_protection():
    """Check CSRF protection status"""
    print("\n🔍 Checking CSRF protection...")
    
    views_file = Path('core/views.py')
    if not views_file.exists():
        print("❌ Views file not found")
        return False
    
    with open(views_file, 'r') as f:
        content = f.read()
    
    csrf_exempt_count = content.count('@csrf_exempt')
    if csrf_exempt_count > 0:
        print(f"⚠️  Found {csrf_exempt_count} CSRF exempt views")
        print("   Consider implementing proper CSRF handling for APIs")
        return False
    else:
        print("✅ No CSRF exempt views found")
        return True

def check_input_validation():
    """Check for input validation"""
    print("\n🔍 Checking input validation...")
    
    views_file = Path('core/views.py')
    if not views_file.exists():
        print("❌ Views file not found")
        return False
    
    with open(views_file, 'r') as f:
        content = f.read()
    
    if 'validate_input' in content:
        print("✅ Input validation function found")
        return True
    else:
        print("❌ No input validation found")
        return False

def check_rate_limiting():
    """Check for rate limiting implementation"""
    print("\n🔍 Checking rate limiting...")
    
    views_file = Path('core/views.py')
    if not views_file.exists():
        print("❌ Views file not found")
        return False
    
    with open(views_file, 'r') as f:
        content = f.read()
    
    if 'check_rate_limit' in content or 'rate_limit' in content:
        print("✅ Rate limiting implementation found")
        return True
    else:
        print("❌ No rate limiting found")
        return False

def check_security_headers():
    """Check for security headers configuration"""
    print("\n🔍 Checking security headers...")
    
    settings_file = Path('TravelHelper/settings.py')
    if not settings_file.exists():
        print("❌ Settings file not found")
        return False
    
    with open(settings_file, 'r') as f:
        content = f.read()
    
    security_settings = [
        'SECURE_SSL_REDIRECT',
        'SECURE_HSTS_SECONDS',
        'SESSION_COOKIE_SECURE',
        'CSRF_COOKIE_SECURE'
    ]
    
    found_settings = []
    for setting in security_settings:
        if setting in content:
            found_settings.append(setting)
    
    if len(found_settings) >= 3:
        print(f"✅ Found {len(found_settings)}/{len(security_settings)} security settings")
        return True
    else:
        print(f"⚠️  Only found {len(found_settings)}/{len(security_settings)} security settings")
        return False

def check_environment_file():
    """Check for .env.example file"""
    print("\n🔍 Checking environment configuration...")
    
    env_example = Path('.env.example')
    if env_example.exists():
        print("✅ .env.example file found")
        
        with open(env_example, 'r') as f:
            content = f.read()
        
        required_vars = ['SECRET_KEY', 'DB_PASSWORD', 'SOA_KEY']
        found_vars = []
        
        for var in required_vars:
            if var in content:
                found_vars.append(var)
        
        if len(found_vars) == len(required_vars):
            print("✅ All required environment variables documented")
            return True
        else:
            print(f"⚠️  Missing some required variables: {set(required_vars) - set(found_vars)}")
            return False
    else:
        print("❌ .env.example file not found")
        return False

def main():
    print("🛡️  TravelHelper Security Validation")
    print("=" * 40)
    
    checks = [
        ("Hardcoded Secrets", check_hardcoded_secrets),
        ("Debug Settings", check_debug_settings),
        ("CSRF Protection", check_csrf_protection),
        ("Input Validation", check_input_validation),
        ("Rate Limiting", check_rate_limiting),
        ("Security Headers", check_security_headers),
        ("Environment Config", check_environment_file),
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        if check_func():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"🛡️  Security Score: {passed}/{total}")
    
    if passed == total:
        print("🎉 All security checks passed!")
        return 0
    elif passed >= total * 0.8:
        print("⚠️  Most security checks passed, but review the warnings above")
        return 0
    else:
        print("❌ Several security issues found. Please address them before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())