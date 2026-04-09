import html
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from database.db import get_db
from utils.display_date import format_display_date


def _fmt(value) -> str:
    if value is None or value == "":
        return "—"
    return str(value)


def get_smtp_settings():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def send_consignment_email(to_email: str, entry: dict, pdf_path: str) -> bool:
    """Send consignment note PDF to consignor email"""
    try:
        settings = get_smtp_settings()

        smtp_host = settings.get("smtp_host", "")
        smtp_port = int(settings.get("smtp_port", 587))
        smtp_user = settings.get("smtp_user", "")
        smtp_password = settings.get("smtp_password", "")
        from_name = settings.get("smtp_from_name", "ARS Consignment System")

        if not smtp_host or not smtp_user:
            print("[EMAIL] SMTP not configured. Skipping email.")
            return False

        print(f"[EMAIL] Connecting to SMTP: {smtp_host}:{smtp_port}")

        msg = MIMEMultipart()
        msg["From"] = f"{from_name} <{smtp_user}>"
        msg["To"] = to_email
        msg["Subject"] = f"Consignment Note #{entry.get('consignment_no')} - Aggarwal Routemaster Services"

        name = entry.get("consignor_name") or "Sir/Madam"
        cno = _fmt(entry.get("consignment_no"))
        date = format_display_date(entry.get("date"))
        frm = _fmt(entry.get("from_location"))
        to_loc = _fmt(entry.get("to_location"))
        desc = _fmt(entry.get("description"))
        pkgs = _fmt(entry.get("no_of_packages"))
        amt = _fmt(entry.get("total_amount"))
        truck = _fmt(entry.get("truck_no"))

        h = html.escape
        name_h = h(name)
        cno_h, date_h = h(cno), h(date)
        frm_h, to_loc_h = h(frm), h(to_loc)
        desc_h, pkgs_h = h(desc), h(pkgs)
        amt_h, truck_h = h(amt), h(truck)

        body_plain = f"""Dear {name},

Thank you for your business. Your consignment note (PDF) is attached to this email.

────────────────────────────────────────
  SHIPMENT SUMMARY
────────────────────────────────────────

  Consignment No.     {cno}
  Date                {date}
  From                {frm}
  To                  {to_loc}
  Description         {desc}
  Packages            {pkgs}
  Total amount        Rs. {amt}
  Truck No.           {truck}

────────────────────────────────────────

Please retain the attached PDF for your records.

Questions? We're here to help:

  Aggarwal Routemaster Services Pvt. Ltd.
  Phone: 9623364953 / 9321115859
  Email: aggarwalroutemaster@gmail.com

Thank you for choosing ARS.

Warm regards,
Aggarwal Routemaster Services Pvt. Ltd.
"""

        body_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;color:#1a1a1a;background:#f5f5f5;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width:560px;background:#ffffff;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
          <tr>
            <td style="background:#1e3a5f;color:#ffffff;padding:16px 20px;font-size:16px;font-weight:600;">
              Consignment note
            </td>
          </tr>
          <tr>
            <td style="padding:20px 20px 8px;">
              <p style="margin:0 0 16px;">Dear {name_h},</p>
              <p style="margin:0 0 16px;">Thank you for your business. Your consignment note (PDF) is attached to this email.</p>
            </td>
          </tr>
          <tr>
            <td style="padding:0 20px 16px;">
              <p style="margin:0 0 8px;font-size:12px;font-weight:600;letter-spacing:0.06em;color:#666;text-transform:uppercase;">Shipment summary</p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8e8e8;border-radius:6px;font-size:14px;">
                <tr><td style="padding:10px 14px;border-bottom:1px solid #eee;color:#555;width:38%;">Consignment No.</td><td style="padding:10px 14px;border-bottom:1px solid #eee;font-weight:500;">{cno_h}</td></tr>
                <tr><td style="padding:10px 14px;border-bottom:1px solid #eee;color:#555;">Date</td><td style="padding:10px 14px;border-bottom:1px solid #eee;font-weight:500;">{date_h}</td></tr>
                <tr><td style="padding:10px 14px;border-bottom:1px solid #eee;color:#555;">From</td><td style="padding:10px 14px;border-bottom:1px solid #eee;font-weight:500;">{frm_h}</td></tr>
                <tr><td style="padding:10px 14px;border-bottom:1px solid #eee;color:#555;">To</td><td style="padding:10px 14px;border-bottom:1px solid #eee;font-weight:500;">{to_loc_h}</td></tr>
                <tr><td style="padding:10px 14px;border-bottom:1px solid #eee;color:#555;vertical-align:top;">Description</td><td style="padding:10px 14px;border-bottom:1px solid #eee;font-weight:500;">{desc_h}</td></tr>
                <tr><td style="padding:10px 14px;border-bottom:1px solid #eee;color:#555;">Packages</td><td style="padding:10px 14px;border-bottom:1px solid #eee;font-weight:500;">{pkgs_h}</td></tr>
                <tr><td style="padding:10px 14px;border-bottom:1px solid #eee;color:#555;">Total amount</td><td style="padding:10px 14px;border-bottom:1px solid #eee;font-weight:500;">Rs. {amt_h}</td></tr>
                <tr><td style="padding:10px 14px;color:#555;">Truck No.</td><td style="padding:10px 14px;font-weight:500;">{truck_h}</td></tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:0 20px 20px;color:#444;font-size:14px;">
              <p style="margin:0 0 16px;">Please retain the attached PDF for your records.</p>
              <p style="margin:0 0 4px;font-size:12px;font-weight:600;color:#666;">Contact</p>
              <p style="margin:0;">Aggarwal Routemaster Services Pvt. Ltd.<br>
              Phone: <a href="tel:9623364953" style="color:#1e3a5f;text-decoration:none;">9623364953</a> / <a href="tel:9321115859" style="color:#1e3a5f;text-decoration:none;">9321115859</a><br>
              Email: <a href="mailto:aggarwalroutemaster@gmail.com" style="color:#1e3a5f;">aggarwalroutemaster@gmail.com</a></p>
              <p style="margin:20px 0 0;">Thank you for choosing ARS.</p>
              <p style="margin:16px 0 0;">Warm regards,<br><strong>Aggarwal Routemaster Services Pvt. Ltd.</strong></p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(body_plain, "plain", "utf-8"))
        alt.attach(MIMEText(body_html, "html", "utf-8"))
        msg.attach(alt)

        # Attach PDF
        pdf_file = Path(pdf_path)
        if pdf_file.exists():
            with open(pdf_file, "rb") as f:
                pdf_data = f.read()
            attachment = MIMEApplication(pdf_data, _subtype="pdf")
            attachment.add_header(
                "Content-Disposition", "attachment",
                filename=f"ConsignmentNote_{entry.get('consignment_no')}.pdf"
            )
            msg.attach(attachment)
            print(f"[EMAIL] PDF attached: {pdf_path}")

        # Send with better error reporting
        print(f"[EMAIL] Authenticating as {smtp_user}...")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        print(f"[EMAIL] SUCCESS - Email sent to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL] AUTH FAILED: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"[EMAIL] SMTP ERROR: {e}")
        return False
    except Exception as e:
        print(f"[EMAIL] ERROR: {type(e).__name__}: {e}")
        return False
