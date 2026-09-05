import os
from playwright.sync_api import sync_playwright
from report_data import get_report_data

REPORTS_DIR = "reports"


def generate_html(data: dict) -> str:
    summary = data["summary"]
    top_products = data["top_products"]
    raw_orders = data["raw_orders"]

    top_rows = ""
    for p in top_products:
        top_rows += f"""
        <tr>
            <td style="font-weight: 600; color: #1e293b;">{p['product']}</td>
            <td style="text-align: right; color: #475569;">{p['count']}</td>
            <td style="text-align: right; font-weight: 600; color: #0f172a;">${p['revenue']:,.2f}</td>
        </tr>
        """

    order_rows = ""
    for o in raw_orders:
        order_rows += f"""
        <tr>
            <td style="color: #64748b; font-family: monospace;">#{o['id']}</td>
            <td style="font-weight: 500;">{o['customer']}</td>
            <td>{o['product']}</td>
            <td style="color: #64748b;">{o['created_at']}</td>
            <td style="text-align: right; font-weight: 600;">${o['amount']:,.2f}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Executive Sales Report</title>
    <style>
        @page {{
            size: A4;
            margin: 22mm 16mm 22mm 16mm;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            color: #0f172a;
            line-height: 1.5;
            font-size: 11.5px;
            margin: 0;
        }}
        .brand-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #0284c7;
            padding-bottom: 12px;
            margin-bottom: 24px;
        }}
        .brand-logo {{
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.5px;
            color: #0369a1;
        }}
        .brand-badge {{
            background: #e0f2fe;
            color: #0369a1;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .metrics-grid {{
            display: flex;
            gap: 16px;
            margin-bottom: 28px;
        }}
        .card {{
            flex: 1;
            padding: 14px 18px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-left: 4px solid #0284c7;
            border-radius: 6px;
        }}
        .card-label {{
            font-size: 10px;
            color: #64748b;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        .card-value {{
            font-size: 22px;
            font-weight: 800;
            color: #0f172a;
            margin-top: 2px;
        }}
        h2 {{
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #cbd5e1;
            padding-bottom: 6px;
            margin-top: 28px;
            margin-bottom: 12px;
            color: #334155;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th, td {{
            padding: 7px 10px;
            border-bottom: 1px solid #f1f5f9;
            text-align: left;
        }}
        th {{
            background: #f8fafc;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #475569;
            border-bottom: 2px solid #e2e8f0;
        }}
        thead {{
            display: table-header-group;
        }}
        tr {{
            break-inside: avoid;
            page-break-inside: avoid;
        }}
    </style>
</head>
<body>
    <div class="brand-header">
        <div>
            <div class="brand-logo">⚡ ShopMetrics</div>
            <div style="color: #64748b; font-size: 11px; margin-top: 2px;">
                Performance period: Last {summary['window_days']} Days | Generated {summary['generated_at']}
            </div>
        </div>
        <div>
            <span class="brand-badge">Automated Report</span>
        </div>
    </div>

    <div class="metrics-grid">
        <div class="card">
            <div class="card-label">Total Revenue</div>
            <div class="card-value">${summary['total_revenue']:,.2f}</div>
        </div>
        <div class="card">
            <div class="card-label">Orders Logged</div>
            <div class="card-value">{summary['total_orders']}</div>
        </div>
        <div class="card">
            <div class="card-label">Avg Order Value</div>
            <div class="card-value">${(summary['total_revenue'] / summary['total_orders'] if summary['total_orders'] > 0 else 0):,.2f}</div>
        </div>
    </div>

    <h2>Top 5 Products by Revenue</h2>
    <table>
        <thead>
            <tr>
                <th>Product</th>
                <th style="text-align: right;">Units Sold</th>
                <th style="text-align: right;">Total Revenue</th>
            </tr>
        </thead>
        <tbody>
            {top_rows}
        </tbody>
    </table>

    <h2>Order Ledger ({len(raw_orders)} records)</h2>
    <table>
        <thead>
            <tr>
                <th>Order ID</th>
                <th>Customer</th>
                <th>Product</th>
                <th>Created At</th>
                <th style="text-align: right;">Amount</th>
            </tr>
        </thead>
        <tbody>
            {order_rows}
        </tbody>
    </table>
</body>
</html>"""


def render_pdf(data: dict, output_path: str) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    html_content = generate_html(data)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template="""
                <div style="font-size: 8px; color: #94a3b8; width: 100%; text-align: right; padding-right: 16mm; font-family: sans-serif;">
                    Page <span class="pageNumber"></span> of <span class="totalPages"></span>
                </div>
            """,
            margin={"top": "22mm", "bottom": "22mm", "left": "16mm", "right": "16mm"},
        )
        browser.close()

    return output_path