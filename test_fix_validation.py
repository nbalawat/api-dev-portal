#!/usr/bin/env python3
"""
Validation script to test if the test fixture issue is fixed.
This script simulates the problematic test sequence.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add app to path for imports
sys.path.append(str(Path(__file__).parent))

# Set test environment
os.environ["TEST_MODE"] = "true"
os.environ["ENVIRONMENT"] = "test"

async def test_fixture_uniqueness():
    """Test that the create_unique_test_user_data function generates unique data."""
    print("🔍 Testing fixture uniqueness...")
    print("=" * 50)
    
    # Import the function
    try:
        from tests.test_integration_auth import create_unique_test_user_data
        print("✅ Successfully imported create_unique_test_user_data")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Generate multiple test data instances
    data_sets = []
    for i in range(5):
        await asyncio.sleep(0.01)  # Small delay to ensure different timestamps
        data = create_unique_test_user_data()
        data_sets.append(data)
        print(f"Dataset {i+1}: {data['username']}, {data['email']}")
    
    # Check for uniqueness
    usernames = [data['username'] for data in data_sets]
    emails = [data['email'] for data in data_sets]
    
    unique_usernames = len(set(usernames))
    unique_emails = len(set(emails))
    
    print(f"\nUniqueness check:")
    print(f"  Usernames: {unique_usernames}/5 unique")
    print(f"  Emails: {unique_emails}/5 unique")
    
    if unique_usernames == 5 and unique_emails == 5:
        print("✅ All data is unique - fixture fix is working!")
        return True
    else:
        print("❌ Data is not unique - fixture fix failed!")
        return False

async def test_sequence_simulation():
    """Simulate the test sequence that was failing."""
    print("\n🧪 Simulating problematic test sequence...")
    print("=" * 50)
    
    try:
        from tests.test_integration_auth import create_unique_test_user_data
        
        # Simulate test_register_new_user
        print("1. Simulating test_register_new_user...")
        test1_data = create_unique_test_user_data()
        print(f"   Test 1 data: {test1_data['username']}")
        
        # Small delay to simulate test execution time
        await asyncio.sleep(0.1)
        
        # Simulate test_register_duplicate_username
        print("2. Simulating test_register_duplicate_username...")
        test2_data = create_unique_test_user_data()
        print(f"   Test 2 data: {test2_data['username']}")
        
        # Check if data is different
        if test1_data['username'] != test2_data['username']:
            print("✅ Tests would use different usernames - no collision!")
            return True
        else:
            print("❌ Tests would use same username - collision detected!")
            return False
            
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        return False

async def main():
    """Main test function."""
    print("🚀 Validating test fixture fix...")
    
    # Test 1: Fixture uniqueness
    test1_passed = await test_fixture_uniqueness()
    
    # Test 2: Sequence simulation  
    test2_passed = await test_sequence_simulation()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION RESULTS")
    print("=" * 50)
    print(f"Fixture uniqueness: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Sequence simulation: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! The fixture fix should resolve the issue.")
        return 0
    else:
        print("\n❌ Some tests failed. The fix may need more work.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)