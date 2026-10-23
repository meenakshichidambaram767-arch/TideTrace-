import re

with open('scripts/ghost_gear.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract stylesheets
css_links = re.findall(r'<link[^>]+href=["\']([^"\']+\.css)["\']', content)
print('CSS Links:', css_links)

# Extract sections and major blocks
sections = re.findall(r'(<(?:section|div)[^>]+id=["\'][^"\']+["\'][^>]*>)', content)
print(f'Total elements with id: {len(sections)}')
for s in sections[:25]:
    print(' ', s)

# Find major headings
headings = re.findall(r'<h[1-4][^>]*>(.*?)</h[1-4]>', content, re.DOTALL)
print('Headings:')
for h in headings[:15]:
    clean = re.sub(r'<[^>]+>', '', h).strip()
    if clean:
        print('  -', clean)
