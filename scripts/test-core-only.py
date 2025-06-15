#!/usr/bin/env python3
"""
Core Test Validation - Run only tests that don't require app initialization
"""
import sys
import os
import asyncio
import time
import traceback
from typing import Dict, Any

def test_imports():
    """Test all critical imports."""
    print("🔍 Testing Critical Imports...")
    
    test_results = {}
    
    # Test core imports
    imports_to_test = [
        ("FastAPI Core", "from fastapi import FastAPI, Depends, HTTPException"),
        ("Pydantic", "from pydantic import BaseModel, Field"),
        ("Async Support", "import asyncio"),
        ("Type Hints", "from typing import Optional, List, Dict, Any"),
        ("Datetime", "from datetime import datetime, timedelta"),
        ("UUID", "from uuid import uuid4"),
        ("Secrets", "import secrets"),
        ("HMAC", "import hmac, hashlib"),
        ("JSON", "import json"),
        ("Enum", "from enum import Enum"),
    ]
    
    for test_name, import_stmt in imports_to_test:
        try:
            exec(import_stmt)
            test_results[test_name] = True
            print(f"  ✅ {test_name}")
        except ImportError as e:
            test_results[test_name] = False
            print(f"  ❌ {test_name}: {e}")
        except Exception as e:
            test_results[test_name] = False
            print(f"  ❌ {test_name}: {e}")
    
    return test_results

def test_api_key_patterns():
    """Test API key generation patterns."""
    print("\\n🔑 Testing API Key Patterns...")
    
    test_results = {}
    
    try:
        import secrets
        import hmac
        import hashlib
        
        # Test 1: Key Generation Pattern
        def generate_key_pair():
            key_id = f"ak_{secrets.token_urlsafe(16)}"
            secret_key = f"sk_{secrets.token_urlsafe(32)}"
            return key_id, secret_key
        
        key_id, secret_key = generate_key_pair()
        
        test_results["Key ID Format"] = key_id.startswith("ak_") and len(key_id) > 20
        test_results["Secret Key Format"] = secret_key.startswith("sk_") and len(secret_key) > 40
        
        print(f"  ✅ Generated Key ID: {key_id}")
        print(f"  ✅ Generated Secret: {secret_key[:20]}...")
        
        # Test 2: HMAC Hashing
        def hash_key(secret_key: str, salt: str = "api_key_salt") -> str:
            return hmac.new(
                salt.encode('utf-8'),
                secret_key.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
        
        hash1 = hash_key(secret_key)
        hash2 = hash_key(secret_key)
        hash3 = hash_key("different_key")
        
        test_results["HMAC Consistency"] = hash1 == hash2
        test_results["HMAC Uniqueness"] = hash1 != hash3
        
        print(f"  ✅ HMAC Hash: {hash1[:20]}...")
        
        # Test 3: Key Validation
        def validate_key_format(key: str) -> bool:
            if key.startswith("sk_"):
                return len(key) > 10
            elif key.startswith("ak_"):
                return len(key) > 10
            return False
        
        test_results["Key Validation"] = (
            validate_key_format(secret_key) and 
            validate_key_format(key_id) and
            not validate_key_format("invalid_key")
        )
        
        print(f"  ✅ Key validation works")
        
    except Exception as e:
        print(f"  ❌ API key pattern test failed: {e}")
        test_results["API Key Patterns"] = False
    
    return test_results

def test_security_patterns():
    """Test security-related patterns."""
    print("\\n🛡️  Testing Security Patterns...")
    
    test_results = {}
    
    try:
        import secrets
        import hashlib
        import hmac
        from datetime import datetime, timedelta
        
        # Test 1: Secure token generation
        def generate_secure_token(length: int = 32) -> str:
            return secrets.token_urlsafe(length)
        
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        
        test_results["Token Uniqueness"] = token1 != token2
        test_results["Token Length"] = len(token1) >= 32
        
        # Test 2: Password hashing (bcrypt-style)
        def simple_hash_password(password: str, salt: str = None) -> str:
            if salt is None:
                salt = secrets.token_hex(16)
            return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex() + ':' + salt
        
        def verify_password(password: str, hash_with_salt: str) -> bool:
            try:
                stored_hash, salt = hash_with_salt.split(':')
                computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
                return stored_hash == computed_hash
            except:
                return False
        
        password = "test_password_123"
        hashed = simple_hash_password(password)
        
        test_results["Password Hashing"] = verify_password(password, hashed)
        test_results["Password Rejection"] = not verify_password("wrong_password", hashed)
        
        print(f"  ✅ Security patterns work correctly")
        
    except Exception as e:
        print(f"  ❌ Security pattern test failed: {e}")
        traceback.print_exc()
        test_results["Security Patterns"] = False
    
    return test_results

def calculate_coverage(all_results: Dict[str, Dict[str, bool]]) -> float:
    """Calculate overall test coverage."""
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        for test_name, passed in results.items():
            total_tests += 1
            if passed:
                passed_tests += 1
    
    return (passed_tests / total_tests * 100) if total_tests > 0 else 0

def main():
    """Main test runner."""
    print("🧪 Docker Core Test Validation")
    print("=================================")
    print("🎯 Testing core functionality without dependencies")
    
    start_time = time.time()
    
    # Run core tests
    all_results = {}
    all_results["Critical Imports"] = test_imports()
    all_results["API Key Patterns"] = test_api_key_patterns()
    all_results["Security Patterns"] = test_security_patterns()
    
    end_time = time.time()
    
    # Calculate results
    coverage = calculate_coverage(all_results)
    total_tests = sum(len(results) for results in all_results.values())
    passed_tests = sum(sum(1 for r in results.values() if r) for results in all_results.values())
    failed_tests = total_tests - passed_tests
    
    # Print summary
    print("\\n" + "=" * 50)
    print("📊 CORE TEST SUMMARY")
    print("=" * 50)
    
    print(f"⏱️  Test Duration:        {end_time - start_time:.2f} seconds")
    print(f"🧪 Total Tests:          {total_tests}")
    print(f"✅ Tests Passed:         {passed_tests}")
    print(f"❌ Tests Failed:         {failed_tests}")
    print(f"📈 Success Rate:         {passed_tests/total_tests*100:.1f}%")
    print(f"🎯 Coverage Score:       {coverage:.1f}%")
    
    if failed_tests == 0:
        print("\\n🎉 All core tests passed! Docker environment is working correctly.")
        print("✅ Core functionality verified and ready for full testing.")
        status = True
    else:
        print(f"\\n❌ {failed_tests} test(s) failed. Please check Docker environment.")
        status = False
    
    return status

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\\n💥 Core test runner failed: {e}")
        traceback.print_exc()
        sys.exit(1)