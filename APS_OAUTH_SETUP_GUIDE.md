# APS OAuth Login Setup Guide

## 📋 Your Current Configuration

✅ **All credentials configured in `.env` file:**

```
Client ID: FrRNFGyGSG90EkcuIDFVHtGoqMcVhM1SMDbp8SeM84oXlAIb
Client Secret: yGfAy7Nqy1E38Z61HNqphvaXu9P6adNnoEm3X2cVYv6a4R1YHgK2FiLUtJpR46iT
Callback URL: http://localhost:3001/aps/oauth/callback
Scopes: data:read, viewables:read
```

---

## 🚀 Step-by-Step Setup Instructions

### Step 1: Access APS Developer Portal

1. Open this URL in your browser:
   ```
   https://aps.autodesk.com/myapps
   ```

2. Sign in with your Autodesk account

3. Find your app with Client ID: `FrRNFGyGSG90EkcuIDFVHtGoqMcVhM1SMDbp8SeM84oXlAIb`
   - If you don't see it, you may need to create a new app or check with the app owner

---

### Step 2: Register Callback URL

1. Click on your app to open app settings

2. Navigate to **"General Settings"** tab

3. Find **"Callback URL"** or **"Redirect URIs"** section

4. Add this **EXACT** URL (copy-paste to avoid typos):
   ```
   http://localhost:3001/aps/oauth/callback
   ```
   
   ⚠️ **Important:**
   - Use `localhost` (NOT `127.0.0.1`)
   - Use `http` (NOT `https`)
   - No trailing slash
   - Port must be `3001`

5. Click **"Save"** or **"Add"**

---

### Step 3: Enable Required APIs

In the same app settings, enable these APIs:

✅ **Data Management API**
- Required for accessing hubs, projects, and files
- Read permissions needed

✅ **Model Derivative API**  
- Required for 3D model viewing
- Read permissions needed

✅ **Authentication API**
- Should be enabled by default
- Required for OAuth flow

Click **"Save"** after enabling APIs.

---

### Step 4: Verify App Configuration

Confirm these settings in your APS app:

| Setting | Required Value |
|---------|----------------|
| **App Type** | Web App |
| **Callback URL** | `http://localhost:3001/aps/oauth/callback` |
| **Data Management API** | Enabled |
| **Model Derivative API** | Enabled |
| **Scopes** | `data:read`, `viewables:read` |

---

### Step 5: Test OAuth Login

1. **Open the application:**
   ```
   http://localhost:5173
   ```

2. **Navigate to the Files tab** or find the ACC Docs Browser section

3. **Click the "Login" button** in the header

4. **You will be redirected to Autodesk sign-in:**
   - Sign in with your Autodesk account
   - Review permissions requested
   - Click **"Allow"** to authorize the app

5. **After authorization:**
   - You'll be redirected back to `http://localhost:5173`
   - The header should show "Logged in"
   - The "Hub" and "Project" dropdowns will become active

---

## ✅ Verification Checklist

After completing the setup, verify:

```powershell
# Check OAuth status
python -c "import requests; r = requests.get('http://127.0.0.1:3001/aps/oauth/status'); print(r.json())"
```

**Before login:** `{"logged_in": false, "expires_at": null}`
**After login:** `{"logged_in": true, "expires_at": "2026-02-15T..."}`

---

## 🔍 Testing Hub Access

After logging in, test hub access:

```powershell
# Get your hubs
python -c "import requests; r = requests.get('http://127.0.0.1:3001/acc/hubs'); print([h['attributes']['name'] for h in r.json()])"
```

This should return a list of your ACC/BIM360 hubs.

---

## 🐛 Troubleshooting

### Issue: "Request Error" when clicking Login

**Cause:** Callback URL not registered in APS portal

**Solution:**
1. Double-check callback URL in APS portal matches exactly: `http://localhost:3001/aps/oauth/callback`
2. Make sure app type is "Web App" (not Desktop or Mobile)
3. Wait 1-2 minutes after saving for changes to propagate

### Issue: "Access Denied" after login

**Cause:** Required APIs not enabled

**Solution:**
1. Go to APS app settings
2. Enable "Data Management API" and "Model Derivative API"
3. Save and try login again

### Issue: "Invalid Scope" error

**Cause:** Requested scopes not allowed for your app

**Solution:**
1. Check scopes in your app settings
2. Make sure `data:read` and `viewables:read` are allowed
3. Contact your APS app administrator if needed

### Issue: Login works but can't see hubs

**Cause:** Account doesn't have access to any ACC/BIM360 hubs

**Solution:**
1. Make sure you're logging in with the correct Autodesk account
2. Verify the account has access to at least one ACC or BIM360 hub
3. Contact your BIM360/ACC administrator to grant access

---

## 📊 Debug OAuth Configuration

Run this to see exact OAuth URL being generated:

```powershell
python -c "import requests, json; r = requests.get('http://127.0.0.1:3001/aps/oauth/debug'); print(json.dumps(r.json(), indent=2))"
```

**Expected output:**
```json
{
  "clientId": "FrRNFGyGSG90EkcuIDFV...",
  "callbackUrl": "http://localhost:3001/aps/oauth/callback",
  "scopes": ["data:read", "viewables:read"],
  "generatedUrl": "https://developer.api.autodesk.com/authentication/v2/authorize?..."
}
```

---

## 🔐 Security Notes

- ✅ Client secret is stored securely in `.env` (not committed to git)
- ✅ OAuth uses standard authorization code flow (PKCE optional)
- ✅ Session stored in memory (APS_STORE=memory)
- ✅ Session TTL: 24 hours (86400 seconds)
- ✅ CORS configured for localhost only

---

## 🎯 What You'll Get After Login

Once logged in successfully, you can:

1. **Browse ACC/BIM360 Content:**
   - View all hubs you have access to
   - Browse projects within each hub
   - List folders and files
   - Filter by file type (IFC, RVT, etc.)

2. **View 3D Models:**
   - Load models directly from ACC/BIM360
   - Use Autodesk Forge Viewer
   - Navigate and inspect 3D geometry

3. **Access File Metadata:**
   - File versions
   - Creation/modification dates
   - File properties
   - Relationships

4. **Process IFC Files:**
   - Extract IFC entities
   - Enrich with bSDD classifications
   - Build knowledge graph
   - Semantic search

---

## 📞 Need Help?

**APS Portal Issues:**
- Visit: https://aps.autodesk.com/support
- Documentation: https://aps.autodesk.com/developer/overview

**Application Issues:**
- Check backend logs: Look at terminal running on port 8001
- Check APS service logs: Look at terminal running on port 3001
- Check frontend console: Open browser DevTools (F12)

**Quick Health Check:**
```powershell
# Run comprehensive system test
cd d:\SMART_BIM
.\.venv\Scripts\Activate.ps1
python test_system.py
```

---

## 📝 Next Steps After Login

1. **Test Hub Access:**
   - Select a hub from dropdown
   - Select a project
   - Browse files

2. **Upload/View Model:**
   - Upload an IFC file
   - View it in the 3D viewer
   - Inspect properties

3. **Enrich Point Cloud:**
   - Upload point cloud (.npy)
   - Run segmentation
   - Enrich with bSDD
   - View semantic data

---

**Last Updated:** February 15, 2026  
**Status:** Ready for OAuth registration  
**Services:** All running (8001, 3001, 5173)
