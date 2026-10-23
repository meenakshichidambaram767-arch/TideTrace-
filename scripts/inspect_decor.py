import re

with open('scripts/ghost_gear.html', 'r', encoding='utf-8') as f:
    html = f.read()

sections = re.findall(r'<section[^>]+class=["\']([^"\']+)["\']', html)
print('All sections:', sections)

# Find all image occurrences across the page to see what decor exists
images = re.findall(r'<img[^>]+class=["\']([^"\']+)["\'][^>]*src=["\']([^"\']+)["\']', html)
print(f'Total img elements: {len(images)}')
for cls, src in images[:25]:
    print(f'  class="{cls}" src="{src}"')
