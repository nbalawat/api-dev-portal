# 🧪 API Key Testing Guide

## Quick Start Testing Plan

### **Phase 1: Setup (5 minutes)**
1. **Start the application**
   ```bash
   # Terminal 1: Start backend
   cd /Users/nbalawat/development/api-developer-portal
   docker-compose up backend

   # Terminal 2: Start frontend  
   cd frontend
   npm run dev
   ```

2. **Open the dashboard**
   - Go to http://localhost:3001
   - Login with demo credentials: `admin@example.com` / `admin123`
   - Navigate to the Dashboard

### **Phase 2: Create Test API Keys (3 minutes)**
1. **Create different types of API keys:**
   - **Production API**: Full permissions (read, write, delete, admin), 10,000/hour rate limit
   - **Development API**: Read + Write permissions, 1,000/hour rate limit  
   - **Testing API**: Read only permissions, 100/hour rate limit
   - **Limited API**: Read only, 10/hour rate limit (for rate limit testing)

2. **Copy the API keys** from the dashboard (use the copy button)

### **Phase 3: Manual Testing (10 minutes)**

#### **Test 1: Basic API Authentication**
```bash
# Replace YOUR_API_KEY with actual key from dashboard
curl -H "X-API-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/v1/profile

# Expected: Should return user profile data
# Check dashboard: "Last Used" should update to "just now"
```

#### **Test 2: Invalid API Key**
```bash
curl -H "X-API-Key: invalid_key_12345" \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/v1/profile

# Expected: Should return 401 Unauthorized
# Check dashboard: Usage stats should NOT change
```

#### **Test 3: Missing API Key**
```bash
curl -H "Content-Type: application/json" \
     http://localhost:8000/api/v1/profile

# Expected: Should return 401 Unauthorized  
```

### **Phase 4: Automated Testing (5 minutes)**
1. **Edit the test script:**
   ```bash
   nano test_api_usage.py
   # Add your API keys to the api_keys list (around line 88)
   ```

2. **Run the automated tests:**
   ```bash
   python3 test_api_usage.py
   ```

3. **Check the dashboard for updates:**
   - Total API Calls should increase
   - Active API Keys count should reflect your keys
   - Recent Activity should show "API Key Used" entries
   - Last Used timestamps should update

### **Phase 5: Real-time Testing (Ongoing)**

#### **Test Dashboard Updates:**
1. Make API calls in Terminal
2. Refresh dashboard to see real-time updates
3. Use the "Refresh" button in Overview
4. Check that stats update immediately

#### **Test Copy Functionality:**
1. Click copy button on any API key
2. Verify green checkmark appears
3. Check for success toast notification
4. Verify "API Key Copied" appears in Recent Activity

#### **Test Edit Functionality:**
1. Edit an API key (change status to inactive)
2. Test API call with that key (should fail)
3. Reactivate the key
4. Test API call again (should work)
5. Check Recent Activity for status changes

## 🎯 Expected Results

### **Dashboard Should Show:**
- ✅ Real request counts (not dummy data)
- ✅ Accurate active API key counts
- ✅ Updated "Last Used" timestamps
- ✅ Recent Activity with real actions
- ✅ Copy feedback with toasts
- ✅ Live status indicators

### **API Responses Should:**
- ✅ Return 200 OK for valid API keys
- ✅ Return 401 Unauthorized for invalid keys
- ✅ Update usage statistics in database
- ✅ Respect rate limiting rules
- ✅ Work with different permission levels

## 🐛 Troubleshooting

### **If API calls fail:**
- Check backend is running on port 8000
- Verify API key is correct (no extra spaces)
- Check network connectivity

### **If dashboard doesn't update:**
- Click the "Refresh" button
- Check browser console for errors
- Verify backend is connected (green indicator)

### **If toasts don't appear:**
- Check browser console for errors
- Try refreshing the page
- Verify you're on a modern browser

## 🎉 Success Criteria

✅ **API Key Creation**: Can create keys with different settings
✅ **Authentication**: Valid keys work, invalid keys fail  
✅ **Real-time Updates**: Dashboard reflects actual usage
✅ **Copy Functionality**: Visual and activity feedback works
✅ **Edit Operations**: Status changes affect API access
✅ **Activity Tracking**: All actions appear in Recent Activity
✅ **Rate Limiting**: Excessive requests are blocked
✅ **Statistics**: Overview shows real data, not dummy values

This comprehensive testing ensures your API Developer Portal is working correctly with real data! 🚀