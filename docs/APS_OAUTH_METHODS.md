# APS OAuth Methods Guide

## 🔐 Two OAuth Flows Available

BIMTwinOps supports **both** 2-legged (server-to-server) and 3-legged (user authorization) OAuth flows. Choose based on your use case.

---

## ✅ Method 1: 2-Legged OAuth (Server-to-Server) - WORKS NOW

**Use Case**: Upload files directly to your OSS bucket without user login

**Status**: ✅ **Working immediately** (no additional config needed)

**Best For**:
- Automated file uploads from scripts/plugins
- Batch processing
- Backend integration
- Revit plugin exports

### Configuration

Your current setup (already configured in [backend/.env](../backend/.env)):

```env
APS_CLIENT_ID=AeX2ADkNpDrn1gI1niESgr6j4WNreGLUZXniyV9LVAJe8CdJ
APS_CLIENT_SECRET=4abjNwA59xEJkpUuA1edAwo87q7wDAatsgmibOPYmglWuwnfbdNA7mnkemIwe28R
APS_BUCKET_KEY=bim-spatial-bhupesh-us-001
APS_OSS_REGION=US
```

✅ **No callback URL needed**
✅ **No user login required** 
✅ **Works immediately**

### How to Use in UI

1. **Open Frontend**: http://localhost:5173
2. **Navigate to**: **"Revit Integration"** tab (left sidebar)
3. **Upload IFC file**:
   - Click "Choose File"
   - Select your `.ifc` file
   - Click "[>>] Upload & Parse"
4. **File uploads to**: `bim-spatial-bhupesh-us-001` bucket automatically

### API Endpoints (2-Legged)

#### Upload File to OSS Bucket
```bash
POST http://localhost:3001/oss/upload

# Example with curl:
curl -X POST http://localhost:3001/oss/upload \
  -F "file=@AC20-FZK-Haus.ifc" \
  -F "bucketKey=bim-spatial-bhupesh-us-001"

# Response:
{
  "bucketKey": "bim-spatial-bhupesh-us-001",
  "objectKey": "AC20-FZK-Haus.ifc",
  "objectId": "urn:adsk.objects:os.object:bim-spatial-bhupesh-us-001/AC20-FZK-Haus.ifc",
  "urn": "dXJuOmFkc2sub2JqZWN0czpvcy5vYmplY3Q6YmltLXNwYXRpYWwtYmh1cGVzaC11cy0wMDEvQUMyMC1GWkstSGF1cy5pZmM"
}
```

#### Get 2-Legged Token (for direct API calls)
```bash
GET http://localhost:3001/aps/token

# Response:
{
  "access_token": "eyJhbGciOiJ...",
  "token_type": "Bearer",
  "expires_in": 3599
}
```

#### Translate to Viewer Format
```bash
POST http://localhost:3001/md/translate
Content-Type: application/json

{
  "urn": "dXJuOmFkc2sub2JqZWN0czpv...",
  "force": false,
  "auth": "app"  // Uses 2-legged token
}
```

---

## 🔒 Method 2: 3-Legged OAuth (User Authorization) - NEEDS SETUP

**Use Case**: Browse user's ACC/BIM 360 projects and files

**Status**: ⚠️ **Requires callback URL registration**

**Best For**:
- Accessing user's ACC projects
- Reading user's BIM 360 files
- Collaborative workflows
- User-specific permissions

### Configuration Required

**Step 1: Register Callback URL**

1. Go to: https://aps.autodesk.com/myapps
2. Select your app: `AeX2ADkNpDrn1gI1niESgr6j4WNreGLUZXniyV9LVAJe8CdJ`
3. Under **"General Settings"** → **"Callback URL"**, add:
   ```
   http://localhost:3001/aps/oauth/callback
   ```
4. Click **Save**

**Step 2: Verify .env Configuration**

Your [backend/.env](../backend/.env) already has these (no changes needed):

```env
APS_CALLBACK_URL=http://localhost:3001/aps/oauth/callback
APS_OAUTH_SCOPES=data:read data:write data:create bucket:create bucket:read viewables:read
```

**Step 3: Restart Services**

```powershell
.\scripts\stop-services.ps1
.\scripts\start-services.ps1
```

### How to Use in UI

1. **Open Frontend**: http://localhost:5173
2. **Navigate to**: **"ACC Docs Browser"** tab (left sidebar)
3. **Click**: **"Login"** button
4. **Autodesk Login**: Opens Autodesk sign-in page
5. **Grant Permissions**: Allow access to your ACC projects
6. **Redirected Back**: After login, you'll see your hubs/projects

### API Endpoints (3-Legged)

#### Initiate Login
```bash
GET http://localhost:3001/aps/oauth/login

# Redirects to Autodesk login page
# After user grants permission, redirects back to:
# http://localhost:3001/aps/oauth/callback?code=...&state=...
```

#### Check Login Status
```bash
GET http://localhost:3001/aps/oauth/status

# Response (logged in):
{
  "logged_in": true,
  "user_info": {
    "user_id": "...",
    "email": "user@example.com"
  }
}

# Response (not logged in):
{
  "logged_in": false
}
```

#### Get User's 3-Legged Token
```bash
GET http://localhost:3001/aps/oauth/token
Cookie: aps_session=<session_id>

# Response:
{
  "access_token": "eyJhbGciOiJ...",
  "token_type": "Bearer",
  "expires_in": 3599
}
```

---

## 📊 Comparison Table

| Feature | 2-Legged OAuth | 3-Legged OAuth |
|---------|----------------|----------------|
| **UI Tab** | Revit Integration | ACC Docs Browser |
| **User Login** | ❌ Not needed | ✅ Required |
| **Callback URL** | ❌ Not needed | ✅ Must be registered |
| **Setup Time** | Immediate | 5 minutes (register callback) |
| **Access Scope** | Your app's bucket | User's ACC projects |
| **Best For** | Automated uploads | User file browsing |
| **Token Lifetime** | 3600 seconds | 3600 seconds |
| **Refresh Token** | ❌ No | ✅ Yes (30 days) |

---

## 🚀 Quick Start (2-Legged - Works Now)

### Option 1: Using the UI

```powershell
# 1. Open frontend
Start-Process http://localhost:5173

# 2. Click "Revit Integration" tab (left sidebar)
# 3. Upload your IFC file
```

### Option 2: Using API

```powershell
# Upload file
curl -X POST http://localhost:3001/oss/upload `
  -F "file=@docs\AC20-FZK-Haus.ifc" `
  -F "bucketKey=bim-spatial-bhupesh-us-001"

# Get the URN from response, then translate
$urn = "dXJuOmFkc2sub2JqZWN0czpv..."
curl -X POST http://localhost:3001/md/translate `
  -H "Content-Type: application/json" `
  -d "{\"urn\":\"$urn\",\"auth\":\"app\"}"
```

---

## 🔧 Troubleshooting

### Error: "https://signin.autodesk.com/request-error"

**Cause**: Callback URL not registered in APS app

**Solution**: 
1. Go to https://aps.autodesk.com/myapps
2. Add callback URL: `http://localhost:3001/aps/oauth/callback`
3. Save and restart services

### Error: "APS credentials not configured"

**Cause**: Missing `APS_CLIENT_ID` or `APS_CLIENT_SECRET`

**Solution**:
```env
# In backend/.env
APS_CLIENT_ID=your_client_id
APS_CLIENT_SECRET=your_client_secret
```

### Upload Works But Can't View Model

**Cause**: Model not translated to viewer format

**Solution**:
```bash
# After upload, translate:
curl -X POST http://localhost:3001/md/translate \
  -H "Content-Type: application/json" \
  -d '{"urn":"YOUR_URN","auth":"app"}'

# Check status:
curl http://localhost:3001/md/manifest?urn=YOUR_URN
```

---

## 📚 Related Documentation

- [APS Developer Portal](https://aps.autodesk.com/myapps)
- [APS OAuth Documentation](https://aps.autodesk.com/en/docs/oauth/v2/tutorials/get-3-legged-token/)
- [Backend Startup Guide](BACKEND_STARTUP_GUIDE.md)
- [Component Architecture](COMPONENT_ARCHITECTURE.md)

---

## ✅ Current Status

**Your BIMTwinOps Setup:**

✅ **2-Legged OAuth**: Working (use Revit Integration tab)
❌ **3-Legged OAuth**: Needs callback URL registration (ACC Docs Browser tab)

**To enable 3-legged OAuth**: Register `http://localhost:3001/aps/oauth/callback` at https://aps.autodesk.com/myapps
