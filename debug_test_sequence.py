#!/usr/bin/env python3
"""
Debug script to reproduce the test sequencing issue.
This script simulates running registration tests in sequence to identify the problem.
"""
import asyncio
import sys
import traceback
from pathlib import Path

# Add app to path for imports
sys.path.append(str(Path(__file__).parent))

async def debug_registration_sequence():
    """Debug the registration sequence issue."""
    print("🔍 Starting debug investigation of test sequence issue...")
    print("=" * 80)
    
    # Import after adding to path
    try:
        from app.models.user import User, EmailVerificationToken
        from app.core.database import init_database, engine, async_session
        from app.core.security import get_password_hash
        from app.routers.auth import register
        from app.dependencies.database import get_database
        from sqlalchemy import select, text
        from sqlalchemy.ext.asyncio import AsyncSession
        import uuid
        
        print("✅ Successfully imported required modules")
    except Exception as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return
    
    # Initialize database
    try:
        print("\n📊 Initializing database connection...")
        init_database()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        traceback.print_exc()
        return
    
    # Test database connection
    try:
        print("\n🔌 Testing database connection...")
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        traceback.print_exc()
        return
    
    # Create test user data
    def create_test_user_data(suffix=""):
        unique_id = str(uuid.uuid4())[:8] + suffix
        return {
            "username": f"testuser_{unique_id}",
            "email": f"test_{unique_id}@example.com",
            "full_name": "Test User",
            "password": "testpassword123",
            "confirm_password": "testpassword123",
            "role": "developer"
        }
    
    # Test 1: First registration (should succeed)
    print("\n" + "="*50)
    print("🧪 TEST 1: First Registration")
    print("="*50)
    
    test1_data = create_test_user_data("_test1")
    print(f"Test data: {test1_data['username']}, {test1_data['email']}")
    
    try:
        async with async_session() as session:
            # Clean database first
            print("🧹 Cleaning database before test 1...")
            await session.execute(text("DELETE FROM email_verification_tokens"))
            await session.execute(text("DELETE FROM users"))
            await session.commit()
            print("✅ Database cleaned")
            
            # Test registration
            from app.models.user import UserRegister
            user_register = UserRegister(**test1_data)
            
            # Simulate the registration endpoint
            print("📝 Attempting first registration...")
            
            # Check if username exists (should not)
            result = await session.execute(select(User).where(User.username == user_register.username))
            existing_user = result.scalar_one_or_none()
            print(f"Username check: {'EXISTS' if existing_user else 'NOT EXISTS'}")
            
            # Check if email exists (should not)
            result = await session.execute(select(User).where(User.email == user_register.email))
            existing_email = result.scalar_one_or_none()
            print(f"Email check: {'EXISTS' if existing_email else 'NOT EXISTS'}")
            
            if existing_user or existing_email:
                print("❌ User/email already exists - this should not happen in clean test")
                return
            
            # Create user
            user = User(
                username=user_register.username,
                email=user_register.email,
                full_name=user_register.full_name,
                hashed_password=get_password_hash(user_register.password),
                role=user_register.role,
                is_active=False,
                is_verified=False
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"✅ User created with ID: {user.id}")
            
            # Create verification token
            verification_token = EmailVerificationToken.create_token(user.id)
            session.add(verification_token)
            await session.commit()
            print(f"✅ Verification token created: {verification_token.token[:10]}...")
            
            print("✅ First registration completed successfully")
            
    except Exception as e:
        print(f"❌ First registration failed: {e}")
        traceback.print_exc()
        return
    
    # Test 2: Second registration with different user (should also succeed)
    print("\n" + "="*50)
    print("🧪 TEST 2: Second Registration (Different User)")
    print("="*50)
    
    test2_data = create_test_user_data("_test2")
    print(f"Test data: {test2_data['username']}, {test2_data['email']}")
    
    try:
        async with async_session() as session:
            # DON'T clean database - simulate test sequence
            print("📝 Attempting second registration (without cleanup)...")
            
            from app.models.user import UserRegister
            user_register = UserRegister(**test2_data)
            
            # Check database state before registration
            users_count = await session.execute(text("SELECT COUNT(*) FROM users"))
            tokens_count = await session.execute(text("SELECT COUNT(*) FROM email_verification_tokens"))
            print(f"Database state: {users_count.scalar()} users, {tokens_count.scalar()} tokens")
            
            # Check if username exists (should not)
            result = await session.execute(select(User).where(User.username == user_register.username))
            existing_user = result.scalar_one_or_none()
            print(f"Username check: {'EXISTS' if existing_user else 'NOT EXISTS'}")
            
            # Check if email exists (should not)  
            result = await session.execute(select(User).where(User.email == user_register.email))
            existing_email = result.scalar_one_or_none()
            print(f"Email check: {'EXISTS' if existing_email else 'NOT EXISTS'}")
            
            if existing_user:
                print(f"❌ PROBLEM: Username {user_register.username} already exists!")
                # Let's see what's in the database
                all_users = await session.execute(select(User))
                for user in all_users.scalars():
                    print(f"  - User: {user.username} ({user.email}) - Active: {user.is_active}")
                return
                
            if existing_email:
                print(f"❌ PROBLEM: Email {user_register.email} already exists!")
                return
            
            # Create second user
            user = User(
                username=user_register.username,
                email=user_register.email,
                full_name=user_register.full_name,
                hashed_password=get_password_hash(user_register.password),
                role=user_register.role,
                is_active=False,
                is_verified=False
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"✅ Second user created with ID: {user.id}")
            
            # Create verification token
            verification_token = EmailVerificationToken.create_token(user.id)
            session.add(verification_token)
            await session.commit()
            print(f"✅ Verification token created: {verification_token.token[:10]}...")
            
            print("✅ Second registration completed successfully")
            
    except Exception as e:
        print(f"❌ Second registration failed: {e}")
        traceback.print_exc()
        
        # Let's examine what's in the database when this fails
        try:
            async with async_session() as debug_session:
                print("\n🔍 Database investigation:")
                all_users = await debug_session.execute(select(User))
                for user in all_users.scalars():
                    print(f"  - User: {user.username} ({user.email}) - Active: {user.is_active}")
                    
                all_tokens = await debug_session.execute(select(EmailVerificationToken))
                for token in all_tokens.scalars():
                    print(f"  - Token: {token.token[:10]}... for user {token.user_id}")
        except Exception as debug_e:
            print(f"❌ Debug investigation failed: {debug_e}")
    
    # Test 3: Try to reproduce the exact test scenario
    print("\n" + "="*50)
    print("🧪 TEST 3: Simulate Exact Test Scenario")
    print("="*50)
    
    try:
        # Clean and run first test
        async with async_session() as session:
            print("🧹 Full cleanup...")
            await session.execute(text("DELETE FROM email_verification_tokens"))
            await session.execute(text("DELETE FROM users"))
            await session.commit()
        
        test3a_data = create_test_user_data("_simulate1")
        test3b_data = create_test_user_data("_simulate2")
        
        # First test simulation
        print(f"📝 Simulating test_register_new_user with {test3a_data['username']}")
        async with async_session() as session:
            from app.models.user import UserRegister
            user_register = UserRegister(**test3a_data)
            
            # Simulate exact registration logic from auth router
            result = await session.execute(select(User).where(User.username == user_register.username))
            if result.scalar_one_or_none():
                print("❌ Username already exists")
                return
                
            result = await session.execute(select(User).where(User.email == user_register.email))
            if result.scalar_one_or_none():
                print("❌ Email already exists") 
                return
            
            user = User(
                username=user_register.username,
                email=user_register.email,
                full_name=user_register.full_name,
                hashed_password=get_password_hash(user_register.password),
                role=user_register.role,
                is_active=False,
                is_verified=False
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            verification_token = EmailVerificationToken.create_token(user.id)
            session.add(verification_token)
            await session.commit()
            
            print("✅ First simulated test passed")
        
        # Second test simulation (this might fail)
        print(f"📝 Simulating test_register_duplicate_username with {test3b_data['username']}")
        async with async_session() as session:
            # This test should pass with different user data
            user_register = UserRegister(**test3b_data)
            
            result = await session.execute(select(User).where(User.username == user_register.username))
            if result.scalar_one_or_none():
                print("❌ UNEXPECTED: Username already exists in clean test")
                return
                
            result = await session.execute(select(User).where(User.email == user_register.email))
            if result.scalar_one_or_none():
                print("❌ UNEXPECTED: Email already exists in clean test")
                return
            
            user = User(
                username=user_register.username,
                email=user_register.email,
                full_name=user_register.full_name,
                hashed_password=get_password_hash(user_register.password),
                role=user_register.role,
                is_active=False,
                is_verified=False
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            verification_token = EmailVerificationToken.create_token(user.id)
            session.add(verification_token)
            await session.commit()
            
            print("✅ Second simulated test passed")
            
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        traceback.print_exc()
    
    # Final database state
    print("\n" + "="*50)
    print("📊 FINAL DATABASE STATE")
    print("="*50)
    
    try:
        async with async_session() as session:
            users_count = await session.execute(text("SELECT COUNT(*) FROM users"))
            tokens_count = await session.execute(text("SELECT COUNT(*) FROM email_verification_tokens"))
            print(f"Final state: {users_count.scalar()} users, {tokens_count.scalar()} tokens")
            
            all_users = await session.execute(select(User))
            for user in all_users.scalars():
                print(f"  - User: {user.username} ({user.email}) - Active: {user.is_active}, Verified: {user.is_verified}")
    except Exception as e:
        print(f"❌ Final state check failed: {e}")
    
    # Cleanup
    try:
        await engine.dispose()
        print("\n✅ Database connection disposed")
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")


if __name__ == "__main__":
    asyncio.run(debug_registration_sequence())