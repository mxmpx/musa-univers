import json
import requests
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE_URL = "https://infoedu.uz/oliygoh"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_page_data():
    """Получает основную страницу и извлекает фильтры и список ВУЗов"""
    try:
        res = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. Извлекаем списки фильтров из селекторов
        selects = soup.find_all('select')
        
        # Регионы
        viloyat_select = soup.find('select', {'aria-label': 'Viloyat'}) or (selects[0] if len(selects) > 0 else None)
        regions = []
        if viloyat_select:
            for opt in viloyat_select.find_all('option'):
                val = opt.get('value', '').strip()
                name = opt.text.strip()
                if val:
                    regions.append({'val': val, 'name': name})

        # Типы ВУЗов
        tur_select = soup.find('select', {'aria-label': 'Universitet turi'}) or (selects[1] if len(selects) > 1 else None)
        types = []
        if tur_select:
            for opt in tur_select.find_all('option'):
                val = opt.get('value', '').strip()
                name = opt.text.strip()
                if val:
                    types.append({'val': val, 'name': name})

        # 2. Извлекаем данные ВУЗов из __NEXT_DATA__
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        nodes = []
        if next_data_script and next_data_script.string:
            try:
                page_data = json.loads(next_data_script.string)
                nodes = page_data.get('props', {}).get('pageProps', {}).get('data', {}).get('contentNodesWithOliygoh', {}).get('nodes', [])
            except json.JSONDecodeError:
                pass

        return regions, types, nodes
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
        return [], [], []

@app.route('/')
def index():
    regions, types, _ = fetch_page_data()
    return render_template('index.html', regions=regions, types=types)

@app.route('/api/filter', methods=['POST'])
def filter_unis():
    req_data = request.json or {}
    selected_region = req_data.get('region', '').lower()
    selected_type = req_data.get('type', '').lower()

    _, _, nodes = fetch_page_data()
    filtered = []

    for node in nodes:
        title = node.get('title', 'Без названия')
        slug = node.get('slug', '')
        info = node.get('oliygohMalumotlari') or {}
        
        node_viloyats = [str(v).lower() for v in info.get('viloyat', [])]
        node_types = [str(t).lower() for t in info.get('universitetTuri', [])]

        # Фильтрация
        match_region = True
        if selected_region and selected_region not in ['barcha viloyatlar', 'barcha', 'all']:
            match_region = any(selected_region in v for v in node_viloyats)

        match_type = True
        if selected_type and selected_type not in ['barcha turlar', 'barcha', 'all']:
            clean_type = selected_type.split(':')[0].strip()
            match_type = any(clean_type in t for t in node_types)

        if match_region and match_type:
            filtered.append({'title': title, 'slug': slug})

    return jsonify({'universities': filtered})

@app.route('/api/details/<slug>', methods=['GET'])
@app.route('/api/details/<slug>', methods=['GET'])
@app.route('/api/details/<slug>', methods=['GET'])
@app.route('/api/details/<slug>', methods=['GET'])
def get_uni_details(slug):
    url = f"https://infoedu.uz/oliygoh/{slug}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        table_items = []

        next_data_script = soup.find('script', id='__NEXT_DATA__')
        if next_data_script and next_data_script.string:
            try:
                page_data = json.loads(next_data_script.string)
                props = page_data.get('props', {}).get('pageProps', {})
                quotas_list = props.get('quotas', [])
                
                if isinstance(quotas_list, list):
                    for q in quotas_list:
                        code = q.get('dirid', '-')
                        dir_name = q.get('dirnm', '-')
                        edu_form = q.get('emnm', '')      # Kunduzgi, Sirtqi...
                        lang = q.get('langnm', '')          # O`zbek, Rus...
                        
                        fan_1 = q.get('fan_1', '') or 'Не указано'
                        fan_2 = q.get('fan_2', '') or 'Не указано'
                        subjects = f"{fan_1}, {fan_2}"
                        
                        # Проверка баллов гранта
                        ball_gr = q.get('ballgr')
                        if not ball_gr or str(ball_gr).strip() in ['0', '0.0', 'None', '']:
                            ball_gr = 'Отсутствует'
                        kv_gr = q.get('grantnm') or '0'
                        
                        # Проверка баллов контракта
                        ball_k = q.get('ballk')
                        if not ball_k or str(ball_k).strip() in ['0', '0.0', 'None', '']:
                            ball_k = 'Отсутствует'
                        kv_k = q.get('contractnm') or '0'
                        
                        desc = f"Kod: {code}. Imtihon fanlari: {subjects}. Grant: {ball_gr} ball, {kv_gr} kvota. Shartnoma: {ball_k} ball, {kv_k} kvota."
                        full_name = f"{dir_name} ({edu_form}, {lang})"
                        
                        table_items.append({
                            'name': full_name,
                            'desc': desc,
                            'fan1': fan_1,
                            'fan2': fan_2
                        })
            except Exception as ex:
                print(f"Ошибка обработки quotas: {ex}")

        return jsonify({'items': table_items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)import json
import requests
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE_URL = "https://infoedu.uz/oliygoh"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_page_data():
    """Получает основную страницу и извлекает фильтры и список ВУЗов"""
    try:
        res = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. Извлекаем списки фильтров из селекторов
        selects = soup.find_all('select')
        
        # Регионы
        viloyat_select = soup.find('select', {'aria-label': 'Viloyat'}) or (selects[0] if len(selects) > 0 else None)
        regions = []
        if viloyat_select:
            for opt in viloyat_select.find_all('option'):
                val = opt.get('value', '').strip()
                name = opt.text.strip()
                if val:
                    regions.append({'val': val, 'name': name})

        # Типы ВУЗов
        tur_select = soup.find('select', {'aria-label': 'Universitet turi'}) or (selects[1] if len(selects) > 1 else None)
        types = []
        if tur_select:
            for opt in tur_select.find_all('option'):
                val = opt.get('value', '').strip()
                name = opt.text.strip()
                if val:
                    types.append({'val': val, 'name': name})

        # 2. Извлекаем данные ВУЗов из __NEXT_DATA__
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        nodes = []
        if next_data_script and next_data_script.string:
            try:
                page_data = json.loads(next_data_script.string)
                nodes = page_data.get('props', {}).get('pageProps', {}).get('data', {}).get('contentNodesWithOliygoh', {}).get('nodes', [])
            except json.JSONDecodeError:
                pass

        return regions, types, nodes
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
        return [], [], []

@app.route('/')
def index():
    regions, types, _ = fetch_page_data()
    return render_template('index.html', regions=regions, types=types)

@app.route('/api/filter', methods=['POST'])
def filter_unis():
    req_data = request.json or {}
    selected_region = req_data.get('region', '').lower()
    selected_type = req_data.get('type', '').lower()

    _, _, nodes = fetch_page_data()
    filtered = []

    for node in nodes:
        title = node.get('title', 'Без названия')
        slug = node.get('slug', '')
        info = node.get('oliygohMalumotlari') or {}
        
        node_viloyats = [str(v).lower() for v in info.get('viloyat', [])]
        node_types = [str(t).lower() for t in info.get('universitetTuri', [])]

        # Фильтрация
        match_region = True
        if selected_region and selected_region not in ['barcha viloyatlar', 'barcha', 'all']:
            match_region = any(selected_region in v for v in node_viloyats)

        match_type = True
        if selected_type and selected_type not in ['barcha turlar', 'barcha', 'all']:
            clean_type = selected_type.split(':')[0].strip()
            match_type = any(clean_type in t for t in node_types)

        if match_region and match_type:
            filtered.append({'title': title, 'slug': slug})

    return jsonify({'universities': filtered})

@app.route('/api/details/<slug>', methods=['GET'])
def get_uni_details(slug):
    url = f"https://infoedu.uz/oliygoh/{slug}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        table_items = []

        for script in json_ld_scripts:
            if script.string:
                try:
                    data = json.loads(script.string)
                    if data.get('@type') == 'Table' and 'hasPart' in data:
                        items = data['hasPart'].get('itemListElement', [])
                        for item in items:
                            table_items.append({
                                'pos': item.get('position', ''),
                                'name': item.get('name', ''),
                                'desc': item.get('description', '')
                            })
                except json.JSONDecodeError:
                    continue

        return jsonify({'items': table_items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
