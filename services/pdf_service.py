from pathlib import Path
import platform
import os
import tempfile
import html as html_module

from utils.display_date import format_display_date

PDF_OUTPUT_DIR = Path("generated_pdfs")
PDF_OUTPUT_DIR.mkdir(exist_ok=True)

# Bundled Devanagari font — wkhtmltopdf does not reliably load remote Google Fonts; @font-face + local file fixes Hindi.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_NOTO_DEVANAGARI_TTF = _PROJECT_ROOT / "static" / "fonts" / "NotoSansDevanagari-Regular.ttf"


def _devanagari_font_face_css() -> str:
    if not _NOTO_DEVANAGARI_TTF.is_file():
        return ""
    # file:// URI so wkhtmltopdf can load glyphs (--enable-local-file-access)
    return f"""@font-face {{
  font-family: "NotoSansDevanagariPDF";
  src: url("{_NOTO_DEVANAGARI_TTF.as_uri()}") format("truetype");
  font-weight: 400;
  font-style: normal;
  font-display: block;
}}"""


def _insurance_checkbox(checked: bool) -> str:
    """High-contrast box + check — tiny &#10003; in 9px cells often disappears in wkhtmltopdf."""
    if checked:
        return '<span class="ins-cb ins-cb-on">&#x2713;</span>'
    return '<span class="ins-cb ins-cb-off"></span>'

# Configure pdfkit with wkhtmltopdf path based on OS
try:
    import pdfkit

    # Detect OS and set wkhtmltopdf path
    if platform.system() == "Windows":
        # Windows: Check common installation paths
        possible_paths = [
            r"D:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
            r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
            r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
        ]
        wkhtmltopdf_path = None
        for path in possible_paths:
            if os.path.exists(path):
                wkhtmltopdf_path = path
                break

        if wkhtmltopdf_path:
            pdfkit_config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        else:
            pdfkit_config = None
    else:
        # Linux: wkhtmltopdf should be in PATH
        pdfkit_config = None

    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False
    pdfkit_config = None

# wkhtmltopdf: landscape A4, tight margins (CSS @page also set)
WKHTMLTOPDF_OPTS = {
    "encoding": "UTF-8",
    "orientation": "Landscape",
    "page-size": "A4",
    "margin-top": "5mm",
    "margin-right": "5mm",
    "margin-bottom": "5mm",
    "margin-left": "5mm",
    # Required for @font-face url(file:///...) when rendering from a temp HTML file
    "enable-local-file-access": "",
}


def _esc(x) -> str:
    if x is None:
        return ""
    return html_module.escape(str(x))


def _fmt_rs(x) -> str:
    if x is None or x == "":
        return ""
    try:
        return f"{float(x):,.2f}"
    except (TypeError, ValueError):
        return _esc(str(x))


def generate_pdf(entry: dict) -> str:
    """Generate consignment note PDF from HTML template using wkhtmltopdf"""
    try:
        if not PDFKIT_AVAILABLE:
            raise ImportError("pdfkit not installed")

        html_content = render_consignment_html(entry)
        output_path = PDF_OUTPUT_DIR / f"consignment_{entry['consignment_no']}.pdf"

        # Convert HTML string to PDF using pdfkit
        # Write to temp HTML file first to avoid encoding issues with special characters
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp:
                tmp.write(html_content)
                tmp_path = tmp.name

            try:
                if pdfkit_config:
                    pdfkit.from_file(
                        tmp_path,
                        str(output_path),
                        configuration=pdfkit_config,
                        options=WKHTMLTOPDF_OPTS,
                    )
                else:
                    pdfkit.from_file(tmp_path, str(output_path), options=WKHTMLTOPDF_OPTS)
                return str(output_path)
            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        except Exception as e:
            # If wkhtmltopdf fails, fall back to HTML
            raise Exception(f"PDF generation failed: {str(e)}")

    except Exception as e:
        # Fallback: save HTML if PDF generation fails
        output_path = PDF_OUTPUT_DIR / f"consignment_{entry['consignment_no']}.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(render_consignment_html(entry))
        return str(output_path)


def render_consignment_html(e: dict) -> str:
    """Landscape HTML matching printed ARS consignment note (wkhtmltopdf-friendly tables)."""
    gst_pct = e.get("gst_percent", 0) or 0
    try:
        g = float(gst_pct)
        gst_row_label = f"GST @ {int(g)} %" if g == int(g) else f"GST @ {g} %"
    except (TypeError, ValueError):
        gst_row_label = f"GST @ {_esc(str(gst_pct))} %"

    _ib = str(e.get("insurance_by") or "owner").strip().lower()
    ins_owner = _ib == "owner"
    ins_cons = _ib == "consignor"
    cb_owner = _insurance_checkbox(ins_owner)
    cb_cons = _insurance_checkbox(ins_cons)

    ins_lines = ""
    if e.get("insurance_company"):
        ins_lines += f'<div class="ins-row">Company: <span class="fill">{_esc(e.get("insurance_company"))}</span></div>'
    if e.get("insurance_policy_no"):
        ins_lines += f'<div class="ins-row">Policy No.: <span class="fill">{_esc(e.get("insurance_policy_no"))}</span></div>'
    if e.get("insurance_amount") not in (None, ""):
        ins_lines += f'<div class="ins-row">Amount: <span class="fill">Rs. {_fmt_rs(e.get("insurance_amount"))}</span></div>'
    ins_lines += '<div class="ins-row">Risk: <span class="fill">&nbsp;</span></div>'

    pkg = e.get("no_of_packages")
    packages_disp = "As Per Invoice" if pkg is None or pkg == "" else _esc(str(pkg))
    freight_rate = _esc(str(e.get("freight_rate") or "Fixed"))
    inv_date_disp = _esc(format_display_date(e.get("invoice_date")))
    cn_date_disp = _esc(format_display_date(e.get("date")))
    eway_exp_disp = _esc(format_display_date(e.get("eway_bill_expiry")))
    _wa = str(e.get("actual_weight") or "").strip()
    _wc = str(e.get("charged_weight") or "").strip()
    weight_txt = f"{_esc(_wa)} / {_esc(_wc)}" if (_wa or _wc) else ""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  {_devanagari_font_face_css()}
  @page {{ size: A4 landscape; margin: 4mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; font-size: 7pt; color: #000; background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  /* Local Noto @font-face + fallbacks (remote fonts are unreliable in wkhtmltopdf) */
  .devanagari {{
    font-family: "NotoSansDevanagariPDF", "Nirmala UI", "Mangal", "Noto Sans Devanagari", Arial, sans-serif;
    font-size: 8.5pt;
    line-height: 1.35;
  }}
  table.form {{ width: 100%; border-collapse: collapse; table-layout: fixed; border: 2px solid #000; }}
  td, th {{ border: 1px solid #000; vertical-align: top; padding: 2px 4px; }}
  .no-border {{ border: none !important; }}
  .center {{ text-align: center; }}
  .right {{ text-align: right; }}
  .blue {{ color: #1a3a6b; }}
  .red {{ color: #c00; }}
  .bold {{ font-weight: bold; }}
  .logo {{ width: 52px; height: 52px; border-radius: 50%; background: #1a3a6b; color: #fff; font-size: 16pt; font-weight: bold; text-align: center; line-height: 52px; margin: 2px auto; }}
  .co-name {{ font-size: 13pt; font-weight: bold; color: #1a3a6b; letter-spacing: 0.5px; line-height: 1.15; }}
  .co-tag {{ font-size: 7.5pt; font-weight: bold; color: #c00; letter-spacing: 1px; margin-top: 2px; }}
  .co-small {{ font-size: 6.5pt; color: #222; margin-top: 2px; line-height: 1.25; }}
  .top-bar {{ font-size: 6.5pt; padding: 1px 4px; }}
  .iso {{ border: 1px solid #888; font-size: 5.5pt; padding: 2px 4px; text-align: center; line-height: 1.2; display: inline-block; }}
  .copy-lbl {{ font-size: 9pt; font-weight: bold; color: #c00; text-align: center; margin: 3px 0; }}
  .gst-big {{ font-size: 8pt; font-weight: bold; color: #c00; text-align: center; }}
  .caution {{ border: 1px solid #c00; color: #c00; font-size: 5.8pt; padding: 3px 4px; line-height: 1.2; margin-bottom: 3px; }}
  .lbl {{ font-size: 6pt; color: #333; }}
  .cn-box {{ border: 2px solid #000; padding: 4px; text-align: center; margin-top: 2px; }}
  .cn-lbl {{ font-size: 7pt; font-weight: bold; color: #c00; }}
  .cn-num {{ font-size: 14pt; font-weight: bold; }}
  .risk-hdr {{ text-align: center; font-weight: bold; font-size: 7pt; padding: 2px; border: 1px solid #000; margin-bottom: 2px; }}
  .ins-title {{ font-weight: bold; text-align: center; font-size: 7pt; }}
  .ins-cb {{ display: inline-block; width: 12px; height: 12px; border: 1.5px solid #000; margin-right: 4px; vertical-align: middle; text-align: center; line-height: 11px; box-sizing: border-box; }}
  .ins-cb-on {{ background: #000; color: #fff; font-size: 9px; font-weight: bold; font-family: Arial, Helvetica, sans-serif; }}
  .ins-cb-off {{ background: #fff; }}
  .ins-row {{ font-size: 6.5pt; margin-top: 2px; }}
  .fill {{ font-weight: bold; }}
  .party-row {{ font-size: 6.5pt; padding: 1px 0; }}
  .party-lbl {{ font-weight: bold; }}
  .main-hdr {{ font-size: 6.5pt; font-weight: bold; text-align: center; background: #f0f0f0; }}
  .main-sub {{ font-size: 5.8pt; color: #444; }}
  .amt-lbl {{ font-size: 6.5pt; }}
  .amt-val {{ font-size: 6.5pt; text-align: right; font-weight: bold; }}
  .total-row td {{ font-weight: bold; border-top: 2px solid #000; font-size: 7pt; background: #f5f5f5; }}
  .sig {{ min-height: 28mm; vertical-align: bottom !important; }}
  .sig-line {{ border-top: 1px solid #000; font-size: 6.5pt; text-align: center; padding-top: 2px; margin-top: 8mm; }}
</style>
</head>
<body>
<table class="form">
  <tr>
    <td colspan="12" class="no-border" style="border-bottom:1px solid #000;">
      <table style="width:100%; border-collapse:collapse;"><tr>
        <td style="width:15%; border:none;" class="top-bar">&nbsp;</td>
        <td style="width:55%; border:none;" class="top-bar center bold"><span class="devanagari" lang="hi">|| जय श्री राम ||</span></td>
        <td style="width:30%; border:none;" class="top-bar right">Mob: 9623364953 / 9321115859 / 9881255568</td>
      </tr></table>
    </td>
  </tr>
  <tr>
    <td colspan="12" class="center bold top-bar" style="font-style:italic;">Subject to Vasai Jurisdiction</td>
  </tr>
  <tr>
    <td rowspan="2" style="width:7%;" class="center">
      <div class="logo">ARS</div>
    </td>
    <td rowspan="2" colspan="8" class="center" style="padding:4px 8px;">
      <div class="co-name">AGGARWAL ROUTEMASTER SERVICES PVT. LTD.</div>
      <div class="co-tag">FLEET OWNERS &amp; TRANSPORT CONTRACTORS</div>
      <div class="co-small bold blue">ISO Certified Company 9001 : 2015</div>
      <div class="co-small">Shop No. 124/125 Infinity Square, Golani Naka, Opp. Varun Industry, Vasai (E), Maharashtra - 401 208.</div>
      <div class="co-small">Email: aggarwalroutemaster@gmail.com | aggarwalroadlinesvasai@gmail.com &nbsp; CIN: U60231MH2020PTC345477</div>
    </td>
    <td colspan="3" class="center" style="width:18%;">
      <span class="iso">ISO<br>9001:2015<br>CERTIFIED</span>
      <div class="co-small" style="margin-top:4px;">Since 1995</div>
    </td>
  </tr>
  <tr>
    <td colspan="3" class="gst-big">GST No.: 27AATCA9935G1Z1</td>
  </tr>
  <tr>
    <td colspan="12" class="copy-lbl">CONSIGNEE COPY</td>
  </tr>

  <!-- Tracking row: caution | insurance | party/route -->
  <tr>
    <td colspan="4" style="width:34%;">
      <div class="caution"><strong>CAUTION:</strong> This consignment will not be detained, diverted, re-routed or re-booked without the consignee bank&apos;s written permission.</div>
      <div class="lbl" style="margin-bottom:2px;">Address of delivery office</div>
      <div class="bold" style="font-size:7.5pt; min-height:14px;">{_esc(str(e.get("to_location") or ""))}</div>
      <div class="lbl" style="margin-top:4px;">DOOR DELIVERY</div>
      <div class="bold" style="font-size:8pt;">{_esc(str(e.get("delivery_type") or "DD"))}</div>
      <div class="cn-box">
        <div class="cn-lbl">CONSIGNMENT NO.</div>
        <div class="cn-num">{_esc(str(e.get("consignment_no") or ""))}</div>
        <div class="lbl">Date</div>
        <div class="bold" style="font-size:10pt;">{cn_date_disp}</div>
      </div>
    </td>
    <td colspan="4" style="width:33%;">
      <div class="risk-hdr">AT OWNER&apos;S RISK</div>
      <div class="ins-title">INSURANCE</div>
      <div style="font-size:6.5pt; margin:2px 0;">The customer has stated that:</div>
      <div style="font-size:6.5pt;">{cb_owner} He has not insured the consignment</div>
      <div style="font-size:6.5pt; margin-top:2px;">{cb_cons} He has insured the consignment</div>
      {ins_lines}
    </td>
    <td colspan="4" style="width:33%;">
      <div class="party-row"><span class="party-lbl">Party Con. No.</span> <span class="fill">&nbsp;</span></div>
      <div class="party-row"><span class="party-lbl">Truck No.</span> <span class="fill">{_esc(str(e.get("truck_no") or ""))}</span></div>
      <div class="party-row"><span class="party-lbl">From</span> <span class="fill">{_esc(str(e.get("from_location") or ""))}</span></div>
      <div class="party-row"><span class="party-lbl">To</span> <span class="fill">{_esc(str(e.get("to_location") or ""))}</span></div>
    </td>
  </tr>

  <tr>
    <td colspan="12">
      <span class="party-lbl">Consignor&apos;s Name &amp; Address</span>
      <span class="red bold"> GST No.</span>
      <div class="bold" style="font-size:7.5pt; margin-top:2px;">{_esc(str(e.get("consignor_name") or ""))}</div>
      <div style="font-size:7pt; min-height:10mm;">{_esc(str(e.get("consignor_address") or ""))}</div>
    </td>
  </tr>
  <tr>
    <td colspan="12">
      <span class="party-lbl">Consignee&apos;s Name &amp; Address</span>
      <div class="bold" style="font-size:7.5pt; margin-top:2px;">{_esc(str(e.get("consignee_name") or ""))}</div>
      <div style="font-size:7pt; min-height:10mm;">{_esc(str(e.get("consignee_address") or ""))}</div>
    </td>
  </tr>

  <!-- Main grid: column headers then one block row (packages/desc/weight/rate + charge lines) -->
  <tr>
    <td colspan="2" class="main-hdr">Packages</td>
    <td colspan="5" class="main-hdr">Description</td>
    <td colspan="2" class="main-hdr">Weight in Kg.<br><span class="main-sub">(Actual / Charged)</span></td>
    <td colspan="1" class="main-hdr">Rate</td>
    <td colspan="2" class="main-hdr">Amount / To Pay / Paid / Due<br><span class="main-sub">(Rs. P.)</span></td>
  </tr>
  <tr>
    <td colspan="2" rowspan="5" class="center bold" style="vertical-align:middle; font-size:8pt;">{packages_disp}</td>
    <td colspan="5" rowspan="5" style="vertical-align:top;">
      <div style="font-size:7.5pt; font-weight:bold; min-height:8mm;">{_esc(str(e.get("description") or ""))}</div>
      <div class="main-sub" style="margin-top:3px;">Invoice No.: <span class="bold" style="color:#000;">{_esc(str(e.get("invoice_no") or ""))}</span></div>
      <div class="main-sub">Date: <span class="bold" style="color:#000;">{inv_date_disp}</span></div>
      <div class="main-sub">GST No.: <span class="bold" style="color:#000;">{_esc(str(e.get("invoice_gst_no") or ""))}</span></div>
      <div class="main-sub">Per: <span class="bold" style="color:#000;">{_esc(str(e.get("invoice_per") or ""))}</span></div>
    </td>
    <td colspan="2" rowspan="5" class="center bold" style="vertical-align:middle; font-size:7.5pt;">{weight_txt}</td>
    <td colspan="1" rowspan="5" class="center bold" style="vertical-align:middle;">{freight_rate}</td>
    <td colspan="1" class="amt-lbl">Freight</td>
    <td colspan="1" class="amt-val">Rs. {_fmt_rs(e.get("freight_amount"))}</td>
  </tr>
  <tr>
    <td colspan="1" class="amt-lbl">Hamali</td>
    <td colspan="1" class="amt-val">Rs. {_fmt_rs(e.get("hamali"))}</td>
  </tr>
  <tr>
    <td colspan="1" class="amt-lbl">{gst_row_label}</td>
    <td colspan="1" class="amt-val">Rs. {_fmt_rs(e.get("gst_amount"))}</td>
  </tr>
  <tr>
    <td colspan="1" class="amt-lbl">St. Charge</td>
    <td colspan="1" class="amt-val">Rs. {_fmt_rs(e.get("st_charge"))}</td>
  </tr>
  <tr class="total-row">
    <td colspan="1" class="amt-lbl">TOTAL</td>
    <td colspan="1" class="amt-val">Rs. {_fmt_rs(e.get("total_amount"))}</td>
  </tr>

  <tr>
    <td colspan="3">
      <span class="lbl">Value Rs.</span>
      <div class="bold" style="font-size:9pt;">{_fmt_rs(e.get("goods_value"))}{' /-' if e.get("goods_value") not in (None, '') else ''}</div>
    </td>
    <td colspan="3">
      <span class="lbl">E-Way Bill</span>
      <div class="bold">{_esc(str(e.get("eway_bill_no") or ""))}</div>
    </td>
    <td colspan="3">
      <span class="lbl">E-Way Bill Exp.</span>
      <div class="bold">{eway_exp_disp}</div>
    </td>
    <td colspan="3" class="sig">
      <div class="sig-line">Signature of the Transport</div>
    </td>
  </tr>
  <tr>
    <td colspan="12" class="center co-small" style="padding:3px;">No responsibility for leakage &amp; breakage</td>
  </tr>
</table>
</body>
</html>"""
