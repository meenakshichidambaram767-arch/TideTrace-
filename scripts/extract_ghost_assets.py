import re

with open('scripts/ghost_gear.html', 'r', encoding='utf-8') as f:
    html = f.read()

vids = re.findall(r'src=["\']([^"\']+\.mp4)["\']', html)
print('Videos:', vids)

imgs = re.findall(r'src=["\']([^"\']+\.(?:webp|png|jpg|svg))["\']', html)
print(f'Total images: {len(imgs)}')
for img in imgs[:20]:
    print(' ', img)

# Also find all chapters and text content
paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
print(f'Total paragraphs: {len(paragraphs)}')
for p in paragraphs[:8]:
    clean = re.sub(r'<[^>]+>', '', p).strip()
    if clean:
        print(' - P:', clean[:100])
