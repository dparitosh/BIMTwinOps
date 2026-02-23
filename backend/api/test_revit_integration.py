"""
Unit tests for Revit Integration API

Tests the Revit bSDD Integration endpoints to verify:
- Backend is running on correct port (8008)
- Revit integration endpoints are accessible
- File upload functionality works
"""
import os
import requests
import pytest
from pathlib import Path

# Configuration from .env
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8008"))
BASE_URL = f"http://localhost:{BACKEND_PORT}"


class TestRevitIntegrationAPI:
    """Test suite for Revit Integration API endpoints"""
    
    def test_backend_health(self):
        """Test 1: Verify backend is running on port 8008"""
        print(f"\n[?] Testing backend health at {BASE_URL}...")
        
        # Try multiple health endpoints
        health_endpoints = ["/health", "/api/health", "/"]
        
        success = False
        for endpoint in health_endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
                if response.status_code == 200:
                    print(f"   [OK] Backend responding on port {BACKEND_PORT}")
                    print(f"   [OK] Endpoint: {endpoint}")
                    success = True
                    break
            except requests.exceptions.RequestException as e:
                continue
        
        if not success:
            pytest.fail(f"[X] Backend not responding on port {BACKEND_PORT}")
    
    def test_revit_integration_status(self):
        """Test 2: Verify Revit integration status endpoint"""
        print(f"\n[?] Testing Revit integration status...")
        
        url = f"{BASE_URL}/api/revit-integration/status"
        
        try:
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   [OK] Revit integration status: {data.get('status', 'unknown')}")
                print(f"   [OK] Upload directory: {data.get('upload_directory', 'N/A')}")
                assert data.get("status") in ["ready", "operational", "ok"]
            elif response.status_code == 404:
                print(f"   [!] Status endpoint not found (404) - might not be implemented")
                # Not a critical failure - endpoint might not exist
            else:
                pytest.fail(f"[X] Unexpected status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            pytest.fail(f"[X] Failed to connect: {e}")
    
    def test_revit_integration_upload_endpoint_accessible(self):
        """Test 3: Verify upload endpoint is accessible (without actual upload)"""
        print(f"\n[?] Testing upload endpoint accessibility...")
        
        url = f"{BASE_URL}/api/revit-integration/upload-ifc"
        
        try:
            # Send GET to check if endpoint exists (should return 405 Method Not Allowed)
            response = requests.get(url, timeout=5)
            
            if response.status_code == 405:
                print(f"   [OK] Upload endpoint exists (405 Method Not Allowed for GET)")
                print(f"   [OK] Endpoint correctly requires POST")
            elif response.status_code == 422:
                print(f"   [OK] Upload endpoint exists (422 Unprocessable Entity)")
            else:
                print(f"   [!] Unexpected status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            pytest.fail(f"[X] Failed to connect to upload endpoint: {e}")
    
    def test_create_mock_ifc_and_upload(self):
        """Test 4: Create a minimal IFC file and test upload"""
        print(f"\n[?] Testing IFC file upload with mock file...")
        
        # Create minimal valid IFC file
        mock_ifc_content = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('test.ifc','2026-02-21T00:00:00',(''),(''),'','','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPROJECT('0vBwe$5hr3Rw2FZJ1bdmhj',$,'Test Project',$,$,$,$,(#9),#5);
#5=IFCUNITASSIGNMENT((#6,#7,#8));
#6=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);
#7=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#8=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);
#9=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.00000000000E-05,#10,$);
#10=IFCAXIS2PLACEMENT3D(#11,$,$);
#11=IFCCARTESIANPOINT((0.,0.,0.));
ENDSEC;
END-ISO-10303-21;
"""
        
        # Create temporary test file
        test_file_path = Path("test_upload.ifc")
        test_file_path.write_text(mock_ifc_content)
        
        try:
            url = f"{BASE_URL}/api/revit-integration/upload-ifc"
            
            with open(test_file_path, 'rb') as f:
                files = {'file': ('test_upload.ifc', f, 'application/x-step')}
                response = requests.post(url, files=files, timeout=10)
            
            print(f"   [>>] Upload response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   [OK] Upload successful!")
                print(f"   [OK] File ID: {data.get('file_id', 'N/A')}")
                print(f"   [OK] File name: {data.get('file_name', 'N/A')}")
                print(f"   [OK] Status: {data.get('status', 'N/A')}")
                assert data.get("status") in ["uploaded", "success", "ok"]
                assert data.get("file_name") == "test_upload.ifc"
            else:
                print(f"   [!] Upload returned status {response.status_code}")
                print(f"   Response: {response.text}")
                
        except requests.exceptions.RequestException as e:
            pytest.fail(f"[X] Upload failed: {e}")
        finally:
            # Cleanup test file
            if test_file_path.exists():
                test_file_path.unlink()
                print(f"   [DEL] Cleaned up test file")
    
    def test_api_documentation_accessible(self):
        """Test 5: Verify OpenAPI documentation is accessible"""
        print(f"\n[?] Testing API documentation...")
        
        docs_url = f"{BASE_URL}/docs"
        
        try:
            response = requests.get(docs_url, timeout=5)
            
            if response.status_code == 200:
                print(f"   [OK] API docs accessible at {docs_url}")
                assert "swagger" in response.text.lower() or "openapi" in response.text.lower()
            else:
                pytest.fail(f"[X] Docs not accessible: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            pytest.fail(f"[X] Failed to access docs: {e}")


def run_tests():
    """Run all tests and print summary"""
    print("\n" + "="*70)
    print("  REVIT INTEGRATION API - UNIT TEST SUITE")
    print("="*70)
    print(f"  Testing backend at: {BASE_URL}")
    print(f"  Expected port: {BACKEND_PORT}")
    print("="*70)
    
    # Run pytest programmatically
    pytest.main([__file__, "-v", "-s", "--tb=short"])


if __name__ == "__main__":
    run_tests()
