"""End-to-end test for the report generation workflow.

Authenticates, uploads a dummy file, triggers report generation,
and polls until completion or failure.

Usage: python tests/test_workflow_e2e.py
"""

import io
import os
import sys
import time

import httpx

BASE_URL = os.environ.get("API_URL", "http://localhost:8000")

# Test user credentials
TEST_EMAIL = os.environ.get("TEST_EMAIL", "test@nitrovia.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "testpassword123")

# Supabase admin access for user confirmation
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://oxhdchbcaczrssryctyi.supabase.co"
)
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def create_dummy_docx() -> bytes:
    """Create a minimal valid .docx file in memory."""
    from zipfile import ZipFile

    buf = io.BytesIO()

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )

    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        '</Relationships>'
    )

    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>'
        '<w:p><w:r><w:t>This is a test document about renewable energy. '
        'Solar and wind power have become the fastest growing energy sources. '
        'According to research, solar capacity has grown by 25% year over year. '
        'Wind energy provides 10% of global electricity needs. '
        'The transition to clean energy is accelerating worldwide. '
        'Investment in renewable energy reached $500 billion in 2025. '
        'Battery storage technology is improving rapidly. '
        'Electric vehicles are becoming mainstream. '
        'Carbon emissions need to be reduced by 50% by 2030. '
        'Many countries have set net-zero targets for 2050.</w:t></w:r></w:p>'
        '</w:body>'
        '</w:document>'
    )

    with ZipFile(buf, 'w') as zf:
        zf.writestr('[Content_Types].xml', content_types)
        zf.writestr('_rels/.rels', rels)
        zf.writestr('word/document.xml', document)

    return buf.getvalue()


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # Step 1: Health check
    print("=" * 60)
    print("STEP 1: Health check")
    print("=" * 60)
    try:
        r = client.get("/health")
        print(f"  Status: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"  FAILED: Cannot reach backend at {BASE_URL}: {e}")
        sys.exit(1)

    # Step 2: Sign up (may fail if user exists, that's fine)
    print("\n" + "=" * 60)
    print("STEP 2: Create test user (or login)")
    print("=" * 60)
    token = None

    # Try signup first
    try:
        r = client.post("/auth/signup", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "full_name": "Test User",
        })
        if r.status_code == 200:
            data = r.json()
            token = data.get("access_token")
            if token:
                print(f"  Signed up successfully. Token: {token[:20]}...")
            else:
                print("  Signed up but no token (email not auto-confirmed)")
        else:
            print(f"  Signup returned {r.status_code} (user may already exist)")
    except Exception as e:
        print(f"  Signup error: {e}")

    # If no token, confirm user via Supabase admin API then login
    if not token and SUPABASE_SERVICE_KEY:
        print("  Confirming user email via admin API...")
        admin = httpx.Client(
            base_url=f"{SUPABASE_URL}/auth/v1",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        # List users to find ours
        try:
            r = admin.get("/admin/users")
            if r.status_code == 200:
                users_data = r.json()
                users_list = users_data.get("users", users_data) if isinstance(users_data, dict) else users_data
                for u in users_list:
                    if u.get("email") == TEST_EMAIL:
                        user_id = u["id"]
                        # Confirm the email
                        r2 = admin.put(f"/admin/users/{user_id}", json={
                            "email_confirm": True,
                        })
                        if r2.status_code == 200:
                            print(f"  Email confirmed for user {user_id}")
                        else:
                            print(f"  Confirm failed: {r2.status_code} {r2.text}")
                        break
        except Exception as e:
            print(f"  Admin API error: {e}")

    # Try login
    if not token:
        try:
            r = client.post("/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            })
            if r.status_code == 200:
                data = r.json()
                token = data.get("access_token")
                print(f"  Logged in successfully. Token: {token[:20]}...")
            else:
                print(f"  Login failed {r.status_code}: {r.text}")
                sys.exit(1)
        except Exception as e:
            print(f"  Login error: {e}")
            sys.exit(1)

    if not token:
        print("  FAILED: Could not obtain auth token")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # Step 3: Upload a dummy file
    print("\n" + "=" * 60)
    print("STEP 3: Upload dummy document")
    print("=" * 60)
    docx_bytes = create_dummy_docx()
    print(f"  Created dummy .docx ({len(docx_bytes)} bytes)")

    r = client.post(
        "/files/upload",
        headers=headers,
        files={"file": ("test_renewable_energy.docx", docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    if r.status_code != 200:
        print(f"  Upload FAILED {r.status_code}: {r.text}")
        sys.exit(1)

    upload_data = r.json()
    file_id = upload_data["file_id"]
    print(f"  Uploaded file_id: {file_id}")

    # Step 4: Trigger report generation
    print("\n" + "=" * 60)
    print("STEP 4: Generate report")
    print("=" * 60)
    r = client.post(
        "/reports/generate",
        headers=headers,
        json={
            "title": "Renewable Energy Trends Test Report",
            "custom_instructions": "Create a brief overview of renewable energy trends.",
            "detail_level": "executive",
            "output_formats": ["pdf"],
            "source_file_ids": [file_id],
        },
    )
    if r.status_code != 200:
        print(f"  Generate FAILED {r.status_code}: {r.text}")
        sys.exit(1)

    gen_data = r.json()
    report_id = gen_data["report_id"]
    print(f"  Report ID: {report_id}")
    print(f"  Status: {gen_data['status']}")
    print(f"  Estimated time: {gen_data['estimated_time_seconds']}s")

    # Step 5: Poll for completion
    print("\n" + "=" * 60)
    print("STEP 5: Polling for completion...")
    print("=" * 60)
    max_wait = 300  # 5 minutes
    poll_interval = 5
    elapsed = 0

    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        r = client.get(f"/reports/{report_id}/status", headers=headers)
        if r.status_code != 200:
            print(f"  Poll error {r.status_code}: {r.text}")
            continue

        status_data = r.json()
        status = status_data.get("status", "unknown")
        progress = status_data.get("progress", 0)
        message = status_data.get("status_message", "")
        error = status_data.get("error_message", "")

        print(f"  [{elapsed:3d}s] status={status} progress={progress}% msg={message}")

        if status == "completed":
            print("\n  *** REPORT COMPLETED SUCCESSFULLY! ***")
            # Fetch full report to confirm
            r = client.get(f"/reports/{report_id}", headers=headers)
            if r.status_code == 200:
                report_data = r.json()
                print(f"  Title: {report_data.get('title')}")
                print(f"  Output files: {report_data.get('output_files')}")
            break
        elif status == "failed":
            print(f"\n  *** REPORT FAILED: {error} ***")
            sys.exit(1)

    else:
        print(f"\n  *** TIMEOUT after {max_wait}s ***")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
