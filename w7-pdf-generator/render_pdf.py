import os
from playwright.sync_api import sync_playwright
from report_data import get_report_data

REPORTS_DIR = "reports"


def generate_html(data: dict) -> str:
    summary = data["summary"]
    top_products = data["top_products"]
    raw_orders = data["raw_orders"]

    # Build Top 5 rows
    top_rows = ""
    for p in top_products:
        top_rows += f"""
        <tr>
            <td>{p['product']}</td>
            <td style="text-align: right;">{p['count']}</td>
            <td style="text-align: right;">${p['revenue']:,.2f}</td>
        </tr>
        """

    # Build All 200 raw order rows (causes multi-page overflow)
    order_rows = ""
    for o in raw_orders:
        order_rows += f"""
        <tr>
            <td>#{o['id']}</td>
            <td>{o['customer']}</td>
            <td>{o['product']}</td>
            <td>{o['created_at']}</td>
            <td style="text-align: right;">${o['amount']:,.2f}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Sales Performance Report</title>
    <style>
        @page {{
            size: A4;
            margin: 20mm 15mm 20mm 15mm;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #1a202c;
            line-height: 1.4;
            font-size: 12px;
        }}
        h1 {{
            font-size: 22px;
            margin-bottom: 4px;
            color: #0f172a;
        }}
        .meta {{
            color: #64748b;
            margin-bottom: 24px;
            font-size: 11px;
        }}
        .metrics-grid {{
            display: flex;
            gap: 16px;
            margin-bottom: 28px;
        }}
        .card {{
            flex: 1;
            padding: 14px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
        }}
        .card-label {{
            font-size: 11px;
            color: #64748b;
            text-transform: uppercase;
            font-weight: 600;
        }}
        .card-value {{
            font-size: 20px;
            font-weight: 700;
            color: #0f172a;
            margin-top: 4px;
        }}
        h2 {{
            font-size: 14px;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 6px;
            margin-top: 24px;
            margin-bottom: 12px;
            color: #1e293b;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th, td {{
            padding: 7px 8px;
            border-bottom: 1px solid #e2e8f0;
            text-align: left;
        }}
        th {{
            background: #f1f5f9;
            font-weight: 600;
            color: #475569;
        }}
        /* Print CSS Trap Fixes */
        thead {{
            display: table-header-group; /* Repeats table header across pages */
        }}
        tr {{
            break-inside: avoid;        /* Prevents row slicing */
            page-break-inside: avoid;
        }}
    </style>
</head>
<body>
    <h1>Sales Performance Report</h1>
    <div class="meta">Generated on: {summary['generated_at']}</div>

    <div class="metrics-grid">
        <div class="card">
            <div class="card-label">Total Revenue</div>
            <div class="card-value">${summary['total_revenue']:,.2f}</div>
        </div>
        <div class="card">
            <div class="card-label">Total Orders</div>
            <div class="card-value">{summary['total_orders']}</div>
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

    <h2>All Orders Log ({len(raw_orders)} records)</h2>
    <table>
        <thead>
            <tr>
                <th>Order ID</th>
                <th>Customer</th>
                <th>Product</th>
                <th>Date</th>
                <th style="text-align: right;">Amount</th>
            </tr>
        </thead>
        <tbody>
            {order_rows}
        </tbody>
    </table>
</body>
</html>"""


def render_pdf(output_path: str = "reports/test.pdf") -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    data = get_report_data()
    html_content = generate_html(data)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
        )
        browser.close()

    print(f"PDF generated: {output_path}")
    return output_path


if __name__ == "__main__":
    render_pdf()