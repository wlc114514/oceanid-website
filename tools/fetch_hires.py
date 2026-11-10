"""下载 Wikimedia Commons 上的高清图和署名信息。用法：python fetch_hires.py 输出目录 "File:标题.jpg" ..."""
import json, sys, time, re, os, urllib.request, urllib.parse
UA = {'User-Agent': 'TIDAL-site-research/1.0 (personal school project)'}
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
meta_path = os.path.join(out, 'credits.json')
meta = json.load(open(meta_path, encoding='utf-8')) if os.path.exists(meta_path) else {}
def get(url):
    for i in range(4):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except Exception: time.sleep(3 * (i + 1))
    raise RuntimeError('下载失败: ' + url)
strip = lambda s: re.sub(r'<[^>]+>', '', s or '').strip()
for t in sys.argv[2:]:
    q = urllib.parse.urlencode(dict(action='query', prop='imageinfo', iiprop='url|extmetadata', iiurlwidth=2400, format='json', titles=t))
    ii = list(json.loads(get('https://commons.wikimedia.org/w/api.php?' + q))['query']['pages'].values())[0]['imageinfo'][0]
    m = ii['extmetadata']
    obj = re.search(r'(RP-[A-Z0-9.\-]+?)(?:\.jpg|\.png|$)', t)
    key = obj.group(1) if obj else t
    open(os.path.join(out, key + '.jpg'), 'wb').write(get(ii['thumburl']))
    meta[key] = {'title': t.removeprefix('File:'), 'artist': strip(m.get('Artist', {}).get('value')),
                 'date': strip(m.get('DateTimeOriginal', {}).get('value')),
                 'license': strip(m.get('LicenseShortName', {}).get('value')), 'source': ii['descriptionurl']}
    print(key, '|', meta[key]['artist'][:60], '|', meta[key]['date'][:30], '|', meta[key]['license'])
    time.sleep(1)
json.dump(meta, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
