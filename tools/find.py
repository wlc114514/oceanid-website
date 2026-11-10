import json, sys, time, urllib.request, urllib.parse, os
out = sys.argv[1]; UA = {'User-Agent': 'TIDAL-site-research/1.0 (personal school project)'}
API = 'https://commons.wikimedia.org/w/api.php?'
def get(params):
    for i in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(API + urllib.parse.urlencode(params), headers=UA), timeout=30)
            return json.load(r)
        except Exception as e:
            time.sleep(3 * (i + 1))
    return None
queries = ['zeemonster RP-P', 'zeepaard RP-P', 'Neptunus zeepaarden RP-P', 'walvis RP-P', 'Nereïde RP-P',
           'kompasroos', 'schip in storm RP-P', 'zeegod RP-P', 'zeegoden en godinnen RP-P', 'Oceanus RP-P']
seen = []
for q in queries:
    d = get(dict(action='query', list='search', srnamespace=6, srlimit=6, format='json', srsearch=q))
    for x in (d or {}).get('query', {}).get('search', []):
        t = x['title']
        if t.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')) and t not in seen: seen.append(t)
    time.sleep(1)
rows = []
for k, t in enumerate(seen):
    d = get(dict(action='query', prop='imageinfo', iiprop='url|extmetadata', iiurlwidth=400, format='json', titles=t))
    if not d: continue
    ii = list(d['query']['pages'].values())[0].get('imageinfo', [{}])[0]
    lic = ii.get('extmetadata', {}).get('LicenseShortName', {}).get('value', '?')
    if 'thumburl' not in ii: continue
    fn = os.path.join(out, f'm{k:02d}.jpg')
    try:
        urllib.request.urlretrieve if False else None
        data = urllib.request.urlopen(urllib.request.Request(ii['thumburl'], headers=UA), timeout=30).read()
        open(fn, 'wb').write(data)
        rows.append({'id': f'm{k:02d}', 'title': t, 'license': lic, 'page': ii.get('descriptionurl', '')})
    except Exception as e:
        print('fail', t, e)
    time.sleep(1)
json.dump(rows, open(os.path.join(out, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in rows: print(r['id'], r['license'], r['title'])
