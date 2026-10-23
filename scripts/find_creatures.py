import re

with open('scripts/ghost_gear.html', 'r', encoding='utf-8') as f:
    html = f.read()

matches = re.findall(r'images/[^\s"\'\)]+', html)
unique_imgs = sorted(list(set(matches)))
print(f'Total unique images: {len(unique_imgs)}')
for img in unique_imgs:
    if any(k in img.lower() for k in ['whale', 'diver', 'ray', 'shark', 'turtle', 'decor', 'fish', 'creature']):
        print(' ', img)

# Also check classes in css
with open('scripts/css_hyundai-ghost-gear.css', 'r', encoding='utf-8') as f:
    css = f.read()

classes = re.findall(r'\.([a-zA-Z0-9\-_]*(?:whale|diver|ray|shark|turtle|fish)[a-zA-Z0-9\-_]*)', css)
print('Creature CSS classes:', sorted(list(set(classes))))
