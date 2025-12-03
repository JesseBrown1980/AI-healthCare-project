# OAuth Implementation Order (Safe, Non-Breaking)

This document outlines the **safest order** to implement OAuth without breaking existing functionality.

## ⚠️ Critical Issue Found

The login endpoint (`/auth/login`) will fail for OAuth users because it tries to verify passwords even when users don't have passwords. We need to fix this **FIRST**.

## Implementation Order

### **Step 1: Fix Login Logic (CRITICAL - Do First)** ✅

**Why First:** Prevents breaking existing password login when OAuth users are added.

**What to do:**
- Update `/auth/login` to check if user has OAuth provider
- Skip password verification for OAuth-only users
- Return appropriate error message

**Risk:** Low - Only adds checks, doesn't change existing behavior

**Files to modify:**
- `backend/api/v1/endpoints/auth.py` - Add OAuth check in login

---

### **Step 2: Create Database Migration** ✅

**Why Second:** Database schema must match code before OAuth can work.

**What to do:**
1. Generate migration: `alembic revision --autogenerate -m "Add OAuth support"`
2. Review migration file (check it adds OAuth columns, makes password_hash nullable)
3. Test migration on development database
4. Apply migration: `alembic upgrade head`

**Risk:** Medium - Database changes, but:
- Makes `password_hash` nullable (safe - existing users have passwords)
- Adds new nullable columns (safe - no data loss)
- Can rollback if needed

**Safety checks:**
- ✅ Backup database first
- ✅ Test on development database
- ✅ Verify existing users still work

---

### **Step 3: Test Existing Functionality** ✅

**Why Third:** Ensure nothing broke after migration.

**What to do:**
1. Test password login (existing users)
2. Test user registration (password-based)
3. Test password reset
4. Run existing auth tests: `pytest tests/test_auth.py -v`

**Risk:** Low - Just testing

**Expected:** All existing functionality should work

---

### **Step 4: Set Environment Variables (Optional for Testing)** ⚠️

**Why Fourth:** OAuth won't work without credentials, but won't break anything.

**What to do:**
- Set Google OAuth variables (optional - can test later)
- Set Apple OAuth variables (optional - can test later)
- Or leave unset - OAuth endpoints will return errors but won't crash

**Risk:** None - Missing env vars just disable OAuth

**Note:** Can skip this step and test OAuth later

---

### **Step 5: Test OAuth Endpoints (Manual)** ✅

**Why Fifth:** Verify OAuth code works before adding UI.

**What to do:**
1. Start backend server
2. Test authorization URL: `GET /auth/oauth/google/authorize`
3. Should redirect to Google (or show error if credentials missing)
4. Test callback endpoint manually (with mock code)

**Risk:** Low - Just testing endpoints

---

### **Step 6: Add Frontend UI Components** ✅

**Why Sixth:** UI is the last step - backend must work first.

**What to do:**
1. Add "Sign in with Google" button to login page
2. Add "Sign in with Apple" button to login page
3. Handle OAuth callback in frontend
4. Store JWT token from callback

**Risk:** Low - Just UI changes, doesn't affect backend

**Files to modify:**
- `frontend/app.py` - Add OAuth buttons
- Or React frontend login component

---

### **Step 7: End-to-End Testing** ✅

**Why Last:** Test the complete flow.

**What to do:**
1. Test Google OAuth flow end-to-end
2. Test Apple OAuth flow end-to-end
3. Test account linking (OAuth + password)
4. Test new OAuth user creation

**Risk:** None - Just testing

---

### **Step 8: Production Enhancements (Later)** ⚠️

**Why Last:** These are optimizations, not required for basic functionality.

**What to do:**
- Encrypt OAuth tokens in database
- Use Redis for state management
- Add token refresh logic
- Add OAuth logout (revoke tokens)

**Risk:** Low - Enhancements only

---

## Quick Start Commands

```bash
# Step 1: Fix login logic (we'll do this now)
# Edit backend/api/v1/endpoints/auth.py

# Step 2: Create and apply migration
alembic revision --autogenerate -m "Add OAuth support to users"
# Review the generated migration file
alembic upgrade head

# Step 3: Test
pytest tests/test_auth.py -v

# Step 4: Set env vars (optional)
export GOOGLE_OAUTH_CLIENT_ID="..."
export GOOGLE_OAUTH_CLIENT_SECRET="..."

# Step 5: Test OAuth endpoints
# Navigate to: http://localhost:8000/auth/oauth/google/authorize

# Step 6: Add UI (we'll do this after testing)
# Edit frontend/app.py

# Step 7: End-to-end test
# Complete OAuth flow in browser
```

## Rollback Plan

If something breaks:

1. **Rollback migration:**
   ```bash
   alembic downgrade -1
   ```

2. **Revert code changes:**
   ```bash
   git checkout HEAD -- backend/api/v1/endpoints/auth.py
   ```

3. **Restore database backup** (if needed)

## Safety Checklist

Before each step:
- [ ] Backup database
- [ ] Run existing tests
- [ ] Test on development environment first
- [ ] Have rollback plan ready

After each step:
- [ ] Verify existing functionality still works
- [ ] Run tests
- [ ] Check logs for errors

