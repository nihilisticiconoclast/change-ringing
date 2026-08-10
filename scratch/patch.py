with open('docs/lineage.html', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('<a href="ringers.html">Ringer Constellation</a>', '<a href="ringers.html">Ringer Constellation</a>\n    <a href="nexus.html">The Temporal Nexus</a>')
with open('docs/lineage.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("patched")
