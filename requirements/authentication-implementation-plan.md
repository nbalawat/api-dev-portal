# Core Authentication Features Implementation Plan

## Overview
This plan details the implementation of a comprehensive authentication and authorization system for the FastAPI Developer Portal, including JWT tokens, role-based access control, and secure user management.

## Architecture Design

### Authentication Flow
```
1. User Registration/Login → Credentials Validation
2. Password Verification → JWT Token Generation  
3. Token Validation → User Context Injection
4. Role-based Authorization → Endpoint Access Control
```

### Security Model
- **JWT Tokens**: Short-lived access tokens (30 min) + longer refresh tokens (7 days)
- **Password Security**: bcrypt hashing with salt rounds
- **Role-based Access**: Admin > Developer > Viewer hierarchy
- **Token Management**: Blacklist for logout, automatic expiration

## Implementation Phases

### Phase 1: Core Foundation (High Priority)

#### Task 1: Module Structure Setup
**Files to Create:**
```
app/
├── core/
│   ├── __init__.py
│   ├── config.py          # Settings and configuration
│   ├── security.py        # JWT and password utilities
│   └── database.py        # Database session management
├── models/
│   ├── __init__.py
│   ├── user.py           # User models and schemas
│   └── token.py          # Token models
├── routers/
│   ├── __init__.py
│   ├── auth.py           # Authentication endpoints
│   └── users.py          # User management endpoints
└── dependencies/
    ├── __init__.py
    ├── auth.py           # Authentication dependencies
    └── database.py       # Database dependencies
```

**Key Components:**
- Pydantic settings configuration
- Database session factory
- FastAPI dependency injection setup

#### Task 2: User Models & Schemas
**SQLModel Entities:**
```python
# User database model
class User(SQLModel, table=True):
    id: UUID = Field(primary_key=True, default_factory=uuid4)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    full_name: Optional[str] = None
    role: UserRole = Field(default=UserRole.developer)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Pydantic Schemas:**
- `UserCreate` - Registration input
- `UserLogin` - Login credentials
- `UserResponse` - Public user data
- `UserUpdate` - Profile updates
- `TokenResponse` - JWT token data

#### Task 3: Password Security
**Implementation:**
- bcrypt hashing with configurable rounds
- Password strength validation
- Secure password verification
- Protection against timing attacks

**Functions:**
```python
def get_password_hash(password: str) -> str
def verify_password(plain_password: str, hashed_password: str) -> bool
def validate_password_strength(password: str) -> bool
```

#### Task 4: JWT Token System
**Token Types:**
- **Access Token**: 30-minute expiry, contains user ID and roles
- **Refresh Token**: 7-day expiry, used to generate new access tokens

**JWT Payload:**
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "role": "developer",
  "exp": 1234567890,
  "iat": 1234567890,
  "jti": "unique_token_id"
}
```

**Functions:**
```python
def create_access_token(data: dict) -> str
def create_refresh_token(user_id: str) -> str
def decode_token(token: str) -> dict
def verify_token(token: str) -> bool
```

#### Task 5: Authentication Router
**Endpoints:**
```python
POST /auth/login          # Login with username/password
POST /auth/refresh        # Refresh access token
POST /auth/logout         # Logout and blacklist token
GET  /auth/me             # Get current user profile
```

**Request/Response Examples:**
```python
# Login Request
{
  "username": "developer",
  "password": "developer123"
}

# Login Response
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Task 6: OAuth2 Dependencies
**FastAPI Security:**
- OAuth2PasswordBearer for token extraction
- OAuth2PasswordRequestForm for login
- Automatic Swagger UI integration

**Dependencies:**
```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User
async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User
```

#### Task 7: Role-Based Access Control
**Role Hierarchy:**
```python
class UserRole(str, Enum):
    admin = "admin"
    developer = "developer"
    viewer = "viewer"
```

**Access Control Decorators:**
```python
def require_role(required_role: UserRole):
    def require_admin() -> User: ...
    def require_developer() -> User: ...
    def require_viewer() -> User: ...
```

**Permission Matrix:**
| Role | User Mgmt | API Keys | Analytics | Admin Panel |
|------|-----------|----------|-----------|-------------|
| Admin | ✅ Full | ✅ All | ✅ All | ✅ Full |
| Developer | ✅ Self | ✅ Own | ✅ Own | ❌ None |
| Viewer | ✅ Read | ❌ None | ✅ Own | ❌ None |

#### Task 8: Database Integration
**Session Management:**
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

**User Repository Pattern:**
```python
class UserRepository:
    async def get_by_username(username: str) -> User | None
    async def get_by_email(email: str) -> User | None
    async def create(user_data: UserCreate) -> User
    async def update(user_id: UUID, user_data: UserUpdate) -> User
```

### Phase 2: Enhanced Features (Medium Priority)

#### Task 9: User Registration
**Registration Flow:**
1. Validate input data (username, email, password)
2. Check for existing users
3. Hash password securely
4. Create user record
5. Send verification email (optional)

**Endpoint:**
```python
POST /auth/register
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "New User"
}
```

#### Task 10: Token Refresh Mechanism
**Refresh Flow:**
1. Validate refresh token
2. Check if token is blacklisted
3. Generate new access token
4. Optionally rotate refresh token

**Security Features:**
- Refresh token rotation
- Automatic cleanup of expired tokens
- Rate limiting on refresh attempts

#### Task 11: Token Blacklist System
**Logout Implementation:**
1. Extract token JTI (unique identifier)
2. Add to blacklist table with expiry
3. Invalidate token immediately

**Blacklist Table:**
```sql
CREATE TABLE token_blacklist (
    id UUID PRIMARY KEY,
    token_jti VARCHAR(255) UNIQUE,
    user_id UUID REFERENCES users(id),
    expires_at TIMESTAMP,
    created_at TIMESTAMP
);
```

#### Task 12: User Profile Management
**Profile Endpoints:**
```python
GET    /users/me           # Get current user profile
PUT    /users/me           # Update profile
PATCH  /users/me/password  # Change password
DELETE /users/me           # Deactivate account
```

**Admin User Management:**
```python
GET    /users/             # List all users (admin)
POST   /users/             # Create user (admin)
PUT    /users/{user_id}    # Update user (admin)
DELETE /users/{user_id}    # Delete user (admin)
```

#### Task 13: Database Migrations
**Alembic Setup:**
```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add authentication tables"

# Apply migration
alembic upgrade head
```

**Migration Integration:**
- Automatic migrations in Docker startup
- Version tracking and rollback support
- Schema validation and testing

#### Task 14: Comprehensive Testing
**Test Categories:**
- **Unit Tests**: Password hashing, JWT generation, validation
- **Integration Tests**: Database operations, authentication flow
- **API Tests**: Endpoint testing with authentication
- **Security Tests**: Token security, role validation

**Test Coverage:**
```python
# Authentication tests
test_password_hashing()
test_jwt_token_creation()
test_login_flow()
test_role_based_access()
test_token_refresh()
test_logout_flow()

# Security tests
test_invalid_tokens()
test_expired_tokens()
test_role_escalation_prevention()
test_rate_limiting()
```

### Phase 3: Documentation & Polish (Low Priority)

#### Task 15: API Documentation Enhancement
**Swagger UI Enhancements:**
- Authentication examples in OpenAPI schema
- JWT token authorization setup
- Role-based endpoint grouping
- Request/response examples

**Documentation Additions:**
- Authentication flow diagrams
- Security best practices
- API usage examples
- Troubleshooting guide

## Security Considerations

### Token Security
- **Short Expiration**: Access tokens expire in 30 minutes
- **Secure Storage**: Tokens stored securely in httpOnly cookies (optional)
- **JTI Tracking**: Unique token IDs for blacklist management
- **Algorithm Security**: RS256 or HS256 with strong secrets

### Password Security
- **bcrypt Hashing**: Industry-standard with salt rounds
- **Strength Validation**: Minimum length, complexity requirements
- **Timing Attack Protection**: Constant-time comparison
- **Rate Limiting**: Login attempt throttling

### Role Security
- **Principle of Least Privilege**: Users get minimum required access
- **Role Validation**: Every endpoint checks user permissions
- **Admin Protection**: Critical operations require admin role
- **Audit Logging**: Role changes and admin actions logged

## Implementation Priority

### High Priority (Must Complete)
1. **Core Authentication** - Login, logout, token validation
2. **User Models** - Database schema and Pydantic models
3. **JWT System** - Token generation and validation
4. **Role-based Access** - Permission system
5. **Database Integration** - Session management

### Medium Priority (Important)
6. **User Registration** - Account creation
7. **Token Refresh** - Session management
8. **Profile Management** - User account updates
9. **Database Migrations** - Schema versioning
10. **Testing Suite** - Quality assurance

### Low Priority (Polish)
11. **Documentation** - Enhanced API docs
12. **Advanced Features** - Email verification, 2FA prep

## Success Criteria

### Functional Requirements
- ✅ Users can register and login successfully
- ✅ JWT tokens are generated and validated correctly
- ✅ Role-based access control works properly
- ✅ Password security meets industry standards
- ✅ Token refresh and logout function correctly

### Security Requirements
- ✅ Passwords are hashed with bcrypt
- ✅ JWT tokens use secure algorithms
- ✅ Access control prevents privilege escalation
- ✅ Tokens can be revoked (blacklisted)
- ✅ All endpoints properly validate authentication

### Performance Requirements
- ✅ Authentication response time < 200ms
- ✅ Token validation overhead < 10ms
- ✅ Database queries optimized with indexes
- ✅ Concurrent user support (100+ simultaneous)

## Next Steps

1. **Review Plan** - Validate approach and priorities
2. **Set Up Development Environment** - Ensure Docker stack is ready
3. **Begin Implementation** - Start with Task 1 (Module Structure)
4. **Incremental Testing** - Test each component as built
5. **Integration** - Connect all pieces and validate end-to-end flow

This implementation will provide a robust, secure authentication system that serves as the foundation for the entire Developer Portal API.