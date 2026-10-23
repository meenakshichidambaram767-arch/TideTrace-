import re

with open('scripts/ghost_gear.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Inspect how images are declared (src might come before class)
images = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', html)
print(f'Total img elements: {len(images)}')
for src in images[:25]:
    print(' ', src)

# Also check how text blocks and headings are styled in each section
for s in ['hero-section', 'video-section', 'article-section first', 'chemspill-section', 'article-section second', 'cta-section']:
    idx = html.find(s)
    if idx != -1:
        snippet = html[idx:idx+600]
        # remove big base64 or svgs
        clean = re.sub(r'<svg[^>]*>.*?</svg>', '[SVG]', snippet, flags=re.DOTALL)
        print('=== Section:', s)
        print(clean[:350])
