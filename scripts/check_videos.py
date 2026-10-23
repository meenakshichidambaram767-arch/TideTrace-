import re

with open('scripts/ghost_gear.html', 'r', encoding='utf-8') as f:
    html = f.read()

matches = re.findall(r'data-video-urls=["\']([^"\']+)["\']', html)
for m in matches:
    print('data-video-urls:', m)

v_srcs = re.findall(r'<source\s+src=["\']([^"\']+)["\']', html)
for s in v_srcs:
    print('source src:', s)

# Also check for webflow asset cdn
cdn_urls = re.findall(r'https://cdn\.prod\.website-files\.com/[^\s"\'\)]+', html)
print(f'Total CDN URLs: {len(cdn_urls)}')
for c in cdn_urls[:10]:
    print(' ', c)
