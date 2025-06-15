#!/usr/bin/env python3
"""
Simple test to validate the fixture fix without external dependencies.
"""
import uuid
import time

def create_unique_test_user_data():
    """Create test user registration data with unique values."""
    import uuid
    import time
    # Use timestamp + uuid to ensure absolute uniqueness between test runs
    timestamp = int(time.time() * 1000) % 100000  # Last 5 digits of timestamp
    unique_id = str(uuid.uuid4())[:8]
    combined_id = f"{timestamp}_{unique_id}"
    return {
        "username": f"testuser_{combined_id}",
        "email": f"test_{combined_id}@example.com",
        "full_name": "Test User",
        "password": "testpassword123",
        "confirm_password": "testpassword123",
        "role": "developer"
    }

def test_uniqueness():
    """Test that the function generates unique data."""
    print("🔍 Testing fixture uniqueness...")
    print("=" * 50)
    
    # Generate multiple test data instances
    data_sets = []
    for i in range(10):
        time.sleep(0.001)  # Small delay to ensure different timestamps
        data = create_unique_test_user_data()
        data_sets.append(data)
        print(f"Dataset {i+1}: {data['username']}")
    
    # Check for uniqueness
    usernames = [data['username'] for data in data_sets]
    emails = [data['email'] for data in data_sets]
    
    unique_usernames = len(set(usernames))
    unique_emails = len(set(emails))
    
    print(f"\nUniqueness check:")
    print(f"  Usernames: {unique_usernames}/10 unique")
    print(f"  Emails: {unique_emails}/10 unique")
    
    if unique_usernames == 10 and unique_emails == 10:
        print("✅ All data is unique - fixture fix is working!")
        return True
    else:
        print("❌ Data is not unique - fixture fix failed!")
        return False

def test_rapid_generation():
    """Test rapid generation to simulate test execution."""
    print("\n🧪 Testing rapid generation (simulating test sequence)...")
    print("=" * 50)
    
    data_sets = []
    for i in range(5):
        # Rapid generation without delay (simulates pytest running tests quickly)
        data = create_unique_test_user_data()
        data_sets.append(data)
    
    usernames = [data['username'] for data in data_sets]
    
    print("Generated usernames:")
    for i, username in enumerate(usernames):
        print(f"  Test {i+1}: {username}")
    
    unique_count = len(set(usernames))
    print(f"\nUnique usernames: {unique_count}/5")
    
    if unique_count == 5:
        print("✅ Rapid generation produces unique data!")
        return True
    else:
        print("❌ Rapid generation has collisions!")
        return False

def main():
    """Main test function."""
    print("🚀 Simple validation of test fixture fix...")
    
    test1_passed = test_uniqueness()
    test2_passed = test_rapid_generation()
    
    print("\n" + "=" * 50)
    print("📊 VALIDATION RESULTS")
    print("=" * 50)
    print(f"Uniqueness test: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Rapid generation: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! The fixture fix should resolve the issue.")
        print("\n📋 SUMMARY OF THE FIX:")
        print("  1. ❌ PROBLEM: test_user_data fixture was cached between tests")
        print("  2. ❌ RESULT: Same username/email used in sequential tests")
        print("  3. ✅ SOLUTION: Use create_unique_test_user_data() function")
        print("  4. ✅ BENEFIT: Each test gets truly unique test data")
        return 0
    else:
        print("\n❌ Some tests failed. The fix may need more work.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)