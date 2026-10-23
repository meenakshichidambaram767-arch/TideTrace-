with open('scripts/convex.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
urls = set(re.findall(r'https?://[^\s"\'\(\)]+\.(?:glb|gltf|mp4|webm|webp|png|jpg)', text))
print(f"Total media: {len(urls)}")
for u in sorted(list(urls))[:20]:
    print(u)
