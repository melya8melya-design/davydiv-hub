from flask import Flask, request, jsonify, render_template_string
import requests
import os

app = Flask(__name__)

MS_BASE = "https://api.moysklad.ru/api/remap/1.2"

def ms_headers():
    return {
        "Authorization": f"Bearer {os.environ.get('MOYSKLAD_TOKEN', '')}",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip"
    }

def get_clients():
    clients = {}
    raw = os.environ.get("CLIENTS", "")
    for line in raw.split(","):
        parts = line.strip().split(":")
        if len(parts) == 3:
            clients[parts[0].strip()] = {
                "name": parts[1].strip(),
                "counterparty_id": parts[2].strip()
            }
    return clients

def stock_label(qty):
    if qty >= 100:
        return ("100+", "high")
    elif qty >= 10:
        return ("10-100", "mid")
    else:
        return ("менше 10", "low")

HTML = '''<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Замовлення</title>
<link href="https://fonts.googleapis.com/css2?family=Geologica:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #f5f3ef;
    --surface: #ffffff;
    --border: #e2ddd6;
    --text: #1a1916;
    --muted: #8a8680;
    --accent: #2d5a27;
    --accent-light: #e8f0e7;
    --high: #2d5a27;
    --mid: #8a6d00;
    --low: #9b2c2c;
    --high-bg: #e8f0e7;
    --mid-bg: #fef9e7;
    --low-bg: #fdecea;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Geologica', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    font-size: 14px;
    line-height: 1.5;
  }
  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 14px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: var(--shadow);
  }
  .logo { font-weight: 600; font-size: 15px; letter-spacing: -0.02em; color: var(--accent); }
  .client-badge { font-size: 12px; color: var(--muted); margin-top: 2px; }
  .total-bar { display: flex; align-items: center; gap: 16px; }
  .total-amount {
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px; font-weight: 500; color: var(--accent);
  }
  .btn-order {
    background: var(--accent); color: white; border: none;
    padding: 8px 20px; border-radius: 8px;
    font-family: 'Geologica', sans-serif; font-size: 13px; font-weight: 500;
    cursor: pointer; transition: opacity 0.15s;
  }
  .btn-order:hover { opacity: 0.85; }
  .btn-order:disabled { opacity: 0.4; cursor: default; }
  main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 80px; }
  .search-bar { margin-bottom: 20px; }
  .search-bar input {
    width: 100%; padding: 10px 16px;
    border: 1px solid var(--border); border-radius: 10px;
    background: var(--surface);
    font-family: 'Geologica', sans-serif; font-size: 14px; color: var(--text);
    outline: none; transition: border-color 0.15s;
  }
  .search-bar input:focus { border-color: var(--accent); }
  .group-section { margin-bottom: 32px; }
  .group-title {
    font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted);
    padding: 0 4px 10px; border-bottom: 1px solid var(--border); margin-bottom: 0;
  }
  table { width: 100%; border-collapse: collapse; background: var(--surface); border-radius: 12px; overflow: hidden; box-shadow: var(--shadow); }
  thead th {
    padding: 10px 14px; text-align: left;
    font-size: 11px; font-weight: 500; letter-spacing: 0.05em; text-transform: uppercase;
    color: var(--muted); background: var(--bg); border-bottom: 1px solid var(--border);
  }
  thead th.right { text-align: right; }
  thead th.center { text-align: center; }
  tbody tr { border-bottom: 1px solid var(--border); transition: background 0.1s; }
  tbody tr:last-child { border-bottom: none; }
  tbody tr:hover { background: #faf9f7; }
  tbody tr.has-qty { background: var(--accent-light); }
  td { padding: 10px 14px; vertical-align: middle; }
  .product-name { font-weight: 400; font-size: 13px; color: var(--text); }
  .product-code { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); margin-top: 2px; }
  .stock-badge {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 11px; font-weight: 500; padding: 3px 8px; border-radius: 20px;
  }
  .stock-badge.high { color: var(--high); background: var(--high-bg); }
  .stock-badge.mid { color: var(--mid); background: var(--mid-bg); }
  .stock-badge.low { color: var(--low); background: var(--low-bg); }
  .dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
  .high .dot { background: var(--high); }
  .mid .dot { background: var(--mid); }
  .low .dot { background: var(--low); }
  .price-cell { font-family: 'JetBrains Mono', monospace; font-size: 13px; text-align: right; white-space: nowrap; }
  .qty-input {
    width: 72px; padding: 6px 10px;
    border: 1px solid var(--border); border-radius: 7px;
    font-family: 'JetBrains Mono', monospace; font-size: 13px;
    text-align: center; color: var(--text); background: white;
    outline: none; transition: border-color 0.15s, box-shadow 0.15s;
    display: block; margin: 0 auto;
  }
  .qty-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(45,90,39,0.1); }
  .qty-input::-webkit-inner-spin-button { -webkit-appearance: none; }
  .sum-cell { font-family: 'JetBrains Mono', monospace; font-size: 13px; text-align: right; font-weight: 500; color: var(--accent); min-width: 90px; }
  .weight-cell { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted); text-align: right; }
  .modal-overlay {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.4); z-index: 200;
    align-items: center; justify-content: center;
  }
  .modal-overlay.open { display: flex; }
  .modal { background: var(--surface); border-radius: 16px; padding: 28px; width: 90%; max-width: 480px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
  .modal h3 { font-size: 18px; font-weight: 600; margin-bottom: 16px; letter-spacing: -0.02em; }
  .modal textarea {
    width: 100%; padding: 10px 14px;
    border: 1px solid var(--border); border-radius: 10px;
    font-family: 'Geologica', sans-serif; font-size: 14px; color: var(--text);
    resize: vertical; min-height: 80px; outline: none; margin-bottom: 16px;
  }
  .modal textarea:focus { border-color: var(--accent); }
  .modal-summary { background: var(--bg); border-radius: 10px; padding: 12px 16px; margin-bottom: 16px; font-size: 13px; max-height: 240px; overflow-y: auto; }
  .modal-summary-row { display: flex; justify-content: space-between; padding: 3px 0; color: var(--muted); }
  .modal-summary-row.total { font-weight: 600; color: var(--text); border-top: 1px solid var(--border); margin-top: 6px; padding-top: 8px; font-size: 14px; }
  .modal-summary-row span:last-child { font-family: 'JetBrains Mono', monospace; }
  .modal-actions { display: flex; gap: 10px; justify-content: flex-end; }
  .btn-cancel {
    background: none; border: 1px solid var(--border); padding: 8px 20px; border-radius: 8px;
    font-family: 'Geologica', sans-serif; font-size: 13px; cursor: pointer; color: var(--muted);
  }
  .btn-cancel:hover { background: var(--bg); }
  .success-msg { display: none; text-align: center; padding: 20px; }
  .success-icon { font-size: 48px; margin-bottom: 12px; }
  .success-msg h3 { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
  .success-msg p { color: var(--muted); font-size: 14px; }
</style>
</head>
<body>
<header>
  <div>
    <div class="logo">Замовлення</div>
    <div class="client-badge">{{ client_name }}</div>
  </div>
  <div class="total-bar">
    <div class="total-amount" id="total-display">0 грн</div>
    <button class="btn-order" id="btn-order" disabled onclick="openModal()">Відправити</button>
  </div>
</header>
<main>
  <div class="search-bar">
    <input type="text" id="search" placeholder="Пошук товару..." oninput="filterProducts()">
  </div>
  <div id="catalog">{{ catalog_html | safe }}</div>
</main>
<div class="modal-overlay" id="modal">
  <div class="modal">
    <div id="modal-form">
      <h3>Підтвердження</h3>
      <div class="modal-summary" id="modal-summary"></div>
      <textarea id="comment" placeholder="Коментар (необов'язково)"></textarea>
      <div class="modal-actions">
        <button class="btn-cancel" onclick="closeModal()">Скасувати</button>
        <button class="btn-order" id="btn-submit" onclick="submitOrder()">Підтвердити</button>
      </div>
    </div>
    <div class="success-msg" id="success-msg">
      <div class="success-icon">✅</div>
      <h3>Замовлення прийнято!</h3>
      <p>Менеджер зв\'яжеться з вами найближчим часом.</p>
      <br>
      <button class="btn-order" onclick="closeModal(); resetOrder()">Нове замовлення</button>
    </div>
  </div>
</div>
<script>
const TOKEN = "{{ token }}";
let total = 0;

function updateTotal() {
  total = 0;
  document.querySelectorAll('.qty-input').forEach(inp => {
    const qty = parseInt(inp.value) || 0;
    const price = parseFloat(inp.dataset.price) || 0;
    const sum = qty * price;
    const row = inp.closest('tr');
    const sumCell = row.querySelector('.sum-cell');
    sumCell.textContent = sum > 0 ? fmt(sum) : '';
    row.classList.toggle('has-qty', qty > 0);
    total += sum;
  });
  document.getElementById('total-display').textContent = fmt(total);
  document.getElementById('btn-order').disabled = total === 0;
}

function fmt(n) {
  return n.toLocaleString('uk-UA', {minimumFractionDigits: 0, maximumFractionDigits: 0}) + ' грн';
}

function filterProducts() {
  const q = document.getElementById('search').value.toLowerCase();
  document.querySelectorAll('.group-section').forEach(section => {
    let vis = false;
    section.querySelectorAll('tbody tr').forEach(row => {
      const name = row.querySelector('.product-name')?.textContent.toLowerCase() || '';
      const show = !q || name.includes(q);
      row.style.display = show ? '' : 'none';
      if (show) vis = true;
    });
    section.style.display = vis ? '' : 'none';
  });
}

function openModal() {
  const items = [];
  document.querySelectorAll('.qty-input').forEach(inp => {
    const qty = parseInt(inp.value) || 0;
    if (qty > 0) items.push({ name: inp.dataset.name, qty, price: parseFloat(inp.dataset.price), sum: qty * parseFloat(inp.dataset.price) });
  });
  let html = '';
  items.forEach(item => {
    const n = item.name.length > 38 ? item.name.substring(0, 38) + '...' : item.name;
    html += `<div class="modal-summary-row"><span>${n} × ${item.qty} ящ.</span><span>${fmt(item.sum)}</span></div>`;
  });
  html += `<div class="modal-summary-row total"><span>Разом</span><span>${fmt(total)}</span></div>`;
  document.getElementById('modal-summary').innerHTML = html;
  document.getElementById('modal-form').style.display = '';
  document.getElementById('success-msg').style.display = 'none';
  document.getElementById('comment').value = '';
  document.getElementById('modal').classList.add('open');
}

function closeModal() { document.getElementById('modal').classList.remove('open'); }

function resetOrder() {
  document.querySelectorAll('.qty-input').forEach(inp => { inp.value = ''; });
  updateTotal();
}

async function submitOrder() {
  const btn = document.getElementById('btn-submit');
  btn.disabled = true;
  btn.textContent = 'Відправляємо...';
  const items = [];
  document.querySelectorAll('.qty-input').forEach(inp => {
    const qty = parseInt(inp.value) || 0;
    if (qty > 0) items.push({ id: inp.dataset.id, qty, price: parseFloat(inp.dataset.price), name: inp.dataset.name });
  });
  try {
    const resp = await fetch('/order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: TOKEN, items, comment: document.getElementById('comment').value })
    });
    const data = await resp.json();
    if (data.ok) {
      document.getElementById('modal-form').style.display = 'none';
      document.getElementById('success-msg').style.display = 'block';
    } else {
      alert('Помилка: ' + (data.error || 'спробуйте ще раз'));
      btn.disabled = false; btn.textContent = 'Підтвердити';
    }
  } catch(e) {
    alert('Помилка з\'єднання. Спробуйте ще раз.');
    btn.disabled = false; btn.textContent = 'Підтвердити';
  }
}
// Poll for changes every 300ms
setInterval(updateTotal, 300);
</script>
</body>
</html>'''

@app.route('/')
def index():
    token = request.args.get('token', '').strip()
    clients = get_clients()

    if not token or token not in clients:
        return '''<html><body style="font-family:sans-serif;display:flex;align-items:center;
        justify-content:center;height:100vh;background:#f5f3ef">
        <div style="text-align:center"><h2 style="color:#9b2c2c">Доступ заборонено</h2>
        <p style="color:#8a8680;margin-top:8px">Перевірте посилання</p></div></body></html>''', 403

    client = clients[token]

    try:
        stock_resp = requests.get(
            f"{MS_BASE}/report/stock/all?filter=stockMode=nonEmpty&limit=1000",
            headers=ms_headers(), timeout=20
        )
        stock_resp.raise_for_status()
        stock_items = stock_resp.json().get("rows", [])

        folders_resp = requests.get(
            f"{MS_BASE}/entity/productfolder?limit=100",
            headers=ms_headers(), timeout=15
        )
        folders_resp.raise_for_status()
        folders = {f["id"]: f["name"] for f in folders_resp.json().get("rows", [])}

        catalog = {}
        for item in stock_items:
            if item.get("stock", 0) <= 0:
                continue
            href = item.get("meta", {}).get("href", "")
            pid = href.split("/")[-1].split("?")[0] if href else ""
            if not pid:
                continue

            price = item.get("salePrice", 0) / 100
            stock = int(item.get("stock", 0))
            folder_href = item.get("folder", {}).get("meta", {}).get("href", "")
            folder_id = folder_href.split("/")[-1] if folder_href else ""
            folder_name = folders.get(folder_id, "Інше")
            top_folder = folder_name.split("/")[0]

            if top_folder not in catalog:
                catalog[top_folder] = []

            catalog[top_folder].append({
                "id": pid,
                "name": item.get("name", ""),
                "code": item.get("code", ""),
                "stock": stock,
                "price": price,
                "weight": item.get("weight", 0),
            })

        html_parts = []
        for folder in sorted(catalog.keys()):
            products = catalog[folder]
            rows = ""
            for p in products:
                label, cls = stock_label(p["stock"])
                price_str = f"{p['price']:,.0f}".replace(",", " ") + " грн" if p["price"] > 0 else "—"
                name_safe = p["name"].replace('"', "&quot;").replace("'", "&#39;")
                weight_str = str(p["weight"]) + " кг" if p["weight"] else "—"
                rows += f'''<tr>
                  <td><div class="product-name">{p["name"]}</div><div class="product-code">{p["code"]}</div></td>
                  <td><span class="stock-badge {cls}"><span class="dot"></span>{label}</span></td>
                  <td class="price-cell">{price_str}</td>
                  <td style="text-align:center"><input class="qty-input" type="number" min="0" step="1" placeholder="0" data-id="{p["id"]}" data-price="{p["price"]}" data-name="{name_safe}" ></td>
                  <td class="sum-cell"></td>
                  <td class="weight-cell">{weight_str}</td>
                </tr>'''

            html_parts.append(f'''<div class="group-section">
              <div class="group-title">{folder}</div>
              <table>
                <thead><tr>
                  <th>Товар</th><th>Залишок</th>
                  <th class="right">Ціна/ящ.</th>
                  <th class="center">Кількість</th>
                  <th class="right">Сума</th>
                  <th class="right">Вага</th>
                </tr></thead>
                <tbody>{rows}</tbody>
              </table>
            </div>''')

        catalog_html = "\n".join(html_parts)

    except Exception as e:
        catalog_html = f'<p style="color:red">Помилка завантаження: {e}</p>'

    return render_template_string(HTML,
        token=token,
        client_name=client["name"],
        catalog_html=catalog_html
    )


@app.route('/order', methods=['POST'])
def create_order():
    data = request.json
    token = data.get("token", "")
    clients = get_clients()

    if token not in clients:
        return jsonify({"ok": False, "error": "Невірний токен"})

    client = clients[token]
    items = data.get("items", [])
    comment = data.get("comment", "")
    org_id = os.environ.get("ORGANIZATION_ID", "")
    counterparty_id = client["counterparty_id"]

    positions = []
    for item in items:
        positions.append({
            "quantity": item["qty"],
            "price": int(float(item["price"]) * 100),
            "assortment": {
                "meta": {
                    "href": f"{MS_BASE}/entity/product/{item['id']}",
                    "type": "product",
                    "mediaType": "application/json"
                }
            }
        })

    order_data = {
        "name": f"Веб: {client['name']}",
        "description": comment,
        "organization": {"meta": {"href": f"{MS_BASE}/entity/organization/{org_id}", "type": "organization", "mediaType": "application/json"}},
        "agent": {"meta": {"href": f"{MS_BASE}/entity/counterparty/{counterparty_id}", "type": "counterparty", "mediaType": "application/json"}},
        "positions": positions
    }

    try:
        resp = requests.post(f"{MS_BASE}/entity/customerorder", headers=ms_headers(), json=order_data, timeout=15)
        resp.raise_for_status()
        return jsonify({"ok": True, "name": resp.json().get("name", "")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
