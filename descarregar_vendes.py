import os, csv, json, time
from datetime import datetime, timedelta
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError

# Configuració (llegeix des de GitHub Secrets / variables d'entorn)
ORG_ID = os.environ.get('SOFYMAN_ORG_ID', '163')
PV_ID = os.environ.get('SOFYMAN_PV_ID', '1')
API_KEY = os.environ.get('SOFYMAN_API_KEY', '')
LOCAL_NOM = os.environ.get('LOCAL_NOM', 'SM Sarria')
ANY = int(os.environ.get('ANY_VENDES', '2026'))

def get_monday(year, fw):
    jan4 = datetime(year, 1, 4)
    start_w1 = jan4 - timedelta(days=(jan4.weekday()))
    return start_w1 + timedelta(weeks=fw - 1)

def last_complete_fw(year):
    today = datetime.now()
    base = get_monday(year, 1)
    days = (today - base).days
    fw = days // 7
    return max(1, fw)

def fetch_week(fw):
    monday = get_monday(ANY, fw)
    sunday = monday + timedelta(days=6)
    fecha_desde = monday.strftime('%Y-%m-%dT00:00:00Z')
    fecha_hasta = sunday.strftime('%Y-%m-%dT23:59:59Z')
    
    params = urlencode({
        'organizationId': ORG_ID,
        'puntoVentaId': PV_ID,
        'apiKey': API_KEY,
        'fechaDesde': fecha_desde,
        'fechaHasta': fecha_hasta,
    })
    url = f'https://app.sofyman.com/api/v2/pedext/get-articulos-con-ventas?{params}'
    
    try:
        with urlopen(url, timeout=30) as r:
            data = json.loads(r.read())
        if not data.get('success'):
            raise Exception(data.get('message', f'Error API fw{fw}'))
        return data['result']
    except HTTPError as e:
        raise Exception(f'HTTP {e.code} a fw{fw}')

def main():
    if not API_KEY:
        raise Exception('SOFYMAN_API_KEY no configurada als GitHub Secrets')
    
    fw_fi = last_complete_fw(ANY)
    print(f'Extraient {LOCAL_NOM} · fw1–fw{fw_fi} · {ANY}')
    
    rows = [['Week', 'LOCAL', 'ID ARTICULO', 'FAMILIA', 'ARTICULO', 'CANTIDAD', 'IMPORTE']]
    
    for fw in range(1, fw_fi + 1):
        print(f'  fw{fw}/{fw_fi}...', end='', flush=True)
        try:
            arts = fetch_week(fw)
            for a in arts:
                rows.append([
                    f'fw{fw}',
                    LOCAL_NOM,
                    a.get('articuloId', ''),
                    a.get('familiaNombre', ''),
                    a.get('articuloNombre', ''),
                    a.get('cantidad', 0),
                    f"{float(a.get('importeTotal', 0)):.2f}"
                ])
            print(f' {len(arts)} articles')
        except Exception as e:
            print(f' ERROR: {e}')
        time.sleep(0.3)
    
    # Desar CSV
    os.makedirs('data', exist_ok=True)
    nom = f"data/SALES_{ANY}_{LOCAL_NOM.replace(' ','')}_fw1-fw{fw_fi}.csv"
    with open(nom, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerows(rows)
    
    print(f'\nFet! {len(rows)-1} línies → {nom}')

if __name__ == '__main__':
    main()
