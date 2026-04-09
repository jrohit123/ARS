from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse, JSONResponse
from database.db import get_db
from utils.templates import get_templates
from services.pdf_service import generate_pdf
from services.email_service import send_consignment_email
import uuid
from datetime import datetime

router = APIRouter()
templates = get_templates()

def require_login(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return user_id

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, saved: int = 0):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse(url="/login")

    conn = get_db()
    role = request.session.get("user_role")

    if role == "admin":
        entries = conn.execute("""
            SELECT c.*, u.full_name as staff_name
            FROM consignments c
            JOIN users u ON c.created_by = u.id
            ORDER BY c.created_at DESC LIMIT 20
        """).fetchall()
    else:
        entries = conn.execute("""
            SELECT c.*, u.full_name as staff_name
            FROM consignments c
            JOIN users u ON c.created_by = u.id
            WHERE c.created_by = ?
            ORDER BY c.created_at DESC LIMIT 20
        """, (user_id,)).fetchall()

    # Stats
    if role == "admin":
        stats = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN DATE(created_at) = DATE('now') THEN 1 ELSE 0 END) as today,
                SUM(email_sent) as emails_sent
            FROM consignments
        """).fetchone()
    else:
        stats = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN DATE(created_at) = DATE('now') THEN 1 ELSE 0 END) as today,
                SUM(email_sent) as emails_sent
            FROM consignments WHERE created_by = ?
        """, (user_id,)).fetchone()

    conn.close()
    return templates.TemplateResponse(request, "dashboard.html", {
        "entries": entries,
        "stats": stats,
        "saved": saved,
        "user_name": request.session.get("user_name"),
        "user_role": role
    })

@router.get("/consignment/new", response_class=HTMLResponse)
async def new_consignment_form(request: Request):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse(url="/login")
    
    # Generate next consignment number
    conn = get_db()
    last = conn.execute("SELECT consignment_no FROM consignments ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    
    if last:
        try:
            num = int(last["consignment_no"]) + 1
        except:
            num = 40096
    else:
        num = 40095
    
    return templates.TemplateResponse(request, "consignment_form.html", {
        "user_name": request.session.get("user_name"),
        "user_role": request.session.get("user_role"),
        "suggested_no": str(num),
        "today": datetime.now().strftime("%Y-%m-%d"),
        "error": None,
        "success": None
    })

@router.post("/consignment/test-save")
async def test_save(request: Request):
    """Debug endpoint - just logs form data"""
    try:
        body = await request.body()
        print(f"[TEST] Raw body size: {len(body)} bytes")
        print(f"[TEST] First 500 chars: {body[:500]}")

        form_data = await request.form()
        print(f"[TEST] Form fields received: {len(form_data)}")
        for key in list(form_data.keys())[:5]:
            print(f"[TEST]   {key}: {form_data[key]}")

        return {"status": "success", "fields_received": len(form_data)}
    except Exception as e:
        print(f"[TEST ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}

@router.post("/consignment/new")
async def save_consignment(request: Request):
    """Save consignment with manual form parsing"""
    print("[SAVE] Endpoint called")

    try:
        user_id = request.session.get("user_id")
        if not user_id:
            print("[SAVE] No user_id in session")
            return RedirectResponse(url="/login")

        print("[SAVE] Parsing form data")
        form_data = await request.form()
        print(f"[SAVE] Got {len(form_data)} form fields")

        # Extract all values
        consignment_no = form_data.get("consignment_no", "")
        date = form_data.get("date", "")
        consignor_name = form_data.get("consignor_name", "")
        consignor_address = form_data.get("consignor_address", "")
        consignor_email = form_data.get("consignor_email", "")
        consignee_name = form_data.get("consignee_name", "")
        consignee_address = form_data.get("consignee_address", "")
        from_location = form_data.get("from_location", "")
        to_location = form_data.get("to_location", "")
        truck_no = form_data.get("truck_no", "")
        description = form_data.get("description", "")
        no_of_packages = form_data.get("no_of_packages", "0")
        actual_weight = form_data.get("actual_weight", "")
        charged_weight = form_data.get("charged_weight", "")
        invoice_no = form_data.get("invoice_no", "")
        invoice_date = form_data.get("invoice_date", "")
        invoice_gst_no = form_data.get("invoice_gst_no", "")
        invoice_per = form_data.get("invoice_per", "")
        goods_value = form_data.get("goods_value", "0")
        delivery_type = form_data.get("delivery_type", "DD")
        insurance_by = form_data.get("insurance_by", "owner")
        insurance_policy_no = form_data.get("insurance_policy_no", "")
        insurance_company = form_data.get("insurance_company", "")
        insurance_amount = form_data.get("insurance_amount", "0")
        freight_rate = form_data.get("freight_rate", "Fixed")
        freight_amount = form_data.get("freight_amount", "0")
        hamali = form_data.get("hamali", "0")
        gst_percent = form_data.get("gst_percent", "0")
        gst_amount = form_data.get("gst_amount", "0")
        st_charge = form_data.get("st_charge", "0")
        total_amount = form_data.get("total_amount", "0")
        eway_bill_no = form_data.get("eway_bill_no", "")
        eway_bill_expiry = form_data.get("eway_bill_expiry", "")

        print(f"[SAVE] CN={consignment_no}")

        conn = get_db()
        print("[SAVE] Inserting into database")
        conn.execute("""
            INSERT INTO consignments (
                consignment_no, date, consignor_name, consignor_address, consignor_email,
                consignee_name, consignee_address, from_location, to_location, truck_no,
                description, no_of_packages, actual_weight, charged_weight,
                invoice_no, invoice_date, invoice_gst_no, invoice_per, goods_value,
                delivery_type, insurance_by, insurance_policy_no, insurance_company, insurance_amount,
                freight_rate, freight_amount, hamali, gst_percent, gst_amount, st_charge, total_amount,
                eway_bill_no, eway_bill_expiry, created_by
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            consignment_no, date, consignor_name, consignor_address, consignor_email,
            consignee_name, consignee_address, from_location, to_location, truck_no,
            description, no_of_packages, actual_weight, charged_weight,
            invoice_no, invoice_date, invoice_gst_no, invoice_per, goods_value,
            delivery_type, insurance_by, insurance_policy_no, insurance_company, insurance_amount,
            freight_rate, freight_amount, hamali, gst_percent, gst_amount, st_charge, total_amount,
            eway_bill_no, eway_bill_expiry, user_id
        ))
        conn.commit()

        print("[SAVE] Getting entry_id")
        entry_id = conn.execute("SELECT id FROM consignments WHERE consignment_no = ?", (consignment_no,)).fetchone()["id"]

        print("[SAVE] Generating PDF")
        entry = conn.execute("SELECT * FROM consignments WHERE id = ?", (entry_id,)).fetchone()
        pdf_path = generate_pdf(dict(entry))

        print("[SAVE] Updating PDF path")
        conn.execute("UPDATE consignments SET pdf_path = ? WHERE id = ?", (pdf_path, entry_id))
        conn.commit()

        conn.close()
        print("[SAVE] SUCCESS - Redirecting to dashboard")
        return RedirectResponse(url="/dashboard?saved=1", status_code=302)

    except Exception as e:
        print(f"[SAVE ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/test-connection")
async def test_connection():
    """Test endpoint to verify server connectivity"""
    print("[TEST] Connection test called")
    return {"status": "server is alive", "time": "now"}


@router.get("/consignment/{entry_id}", response_class=HTMLResponse)
async def view_consignment(request: Request, entry_id: int, success: int = 0, email_result: str = None):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse(url="/login")

    conn = get_db()
    role = request.session.get("user_role")

    if role == "admin":
        entry = conn.execute("SELECT c.*, u.full_name as staff_name FROM consignments c JOIN users u ON c.created_by = u.id WHERE c.id = ?", (entry_id,)).fetchone()
    else:
        entry = conn.execute("SELECT c.*, u.full_name as staff_name FROM consignments c JOIN users u ON c.created_by = u.id WHERE c.id = ? AND c.created_by = ?", (entry_id, user_id)).fetchone()

    conn.close()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    return templates.TemplateResponse(request, "view_consignment.html", {
        "entry": entry,
        "success": success,
        "email_result": email_result,
        "user_name": request.session.get("user_name"),
        "user_role": role
    })

@router.get("/consignment/{entry_id}/pdf")
async def download_pdf(request: Request, entry_id: int):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse(url="/login")

    conn = get_db()
    role = request.session.get("user_role")

    if role == "admin":
        entry = conn.execute("SELECT * FROM consignments WHERE id = ?", (entry_id,)).fetchone()
    else:
        entry = conn.execute("SELECT * FROM consignments WHERE id = ? AND created_by = ?", (entry_id, user_id)).fetchone()

    conn.close()
    if not entry:
        raise HTTPException(status_code=404)

    if not entry["pdf_path"]:
        pdf_path = generate_pdf(dict(entry))
        conn = get_db()
        conn.execute("UPDATE consignments SET pdf_path = ? WHERE id = ?", (pdf_path, entry_id))
        conn.commit()
        conn.close()
    else:
        pdf_path = entry["pdf_path"]

    # Detect file type and serve with correct media type
    media_type = "text/html" if pdf_path.endswith(".html") else "application/pdf"
    filename = pdf_path.split("/")[-1]

    return FileResponse(pdf_path, media_type=media_type, filename=filename)

@router.post("/consignment/{entry_id}/resend-email")
async def resend_consignment_email(request: Request, entry_id: int):
    user_id = require_login(request)
    if not user_id:
        return RedirectResponse(url="/login")

    conn = get_db()
    role = request.session.get("user_role")

    if role == "admin":
        entry = conn.execute("SELECT * FROM consignments WHERE id = ?", (entry_id,)).fetchone()
    else:
        entry = conn.execute("SELECT * FROM consignments WHERE id = ? AND created_by = ?", (entry_id, user_id)).fetchone()

    if not entry:
        conn.close()
        raise HTTPException(status_code=404)

    if not entry["consignor_email"]:
        conn.close()
        return RedirectResponse(url=f"/consignment/{entry_id}?error=no_email", status_code=302)

    # Ensure PDF exists
    pdf_path = entry["pdf_path"]
    if not pdf_path:
        pdf_path = generate_pdf(dict(entry))
        conn.execute("UPDATE consignments SET pdf_path = ? WHERE id = ?", (pdf_path, entry_id))
        conn.commit()

    # Send email
    try:
        email_sent = send_consignment_email(entry["consignor_email"], dict(entry), pdf_path)
        if email_sent:
            conn.execute("UPDATE consignments SET email_sent = 1 WHERE id = ?", (entry_id,))
            conn.commit()
        result = "success" if email_sent else "failed"
    except Exception as e:
        print(f"⚠️ Email resend error: {e}")
        result = "failed"

    conn.close()
    return RedirectResponse(url=f"/consignment/{entry_id}?email_result={result}", status_code=302)
