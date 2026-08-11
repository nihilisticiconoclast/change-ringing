import subprocess

scripts = [
    'scripts/build_atlas.py',
    'scripts/build_geometry_page.py',
    'scripts/build_lineage_atlas.py',
    'scripts/build_method_atlas.py',
    'scripts/build_name_lexicon.py',
    'scripts/build_nexus_page.py',
    'scripts/build_occasions_page.py',
    'scripts/build_ringers_page.py'
]

for script in scripts:
    print(f'Building {script}...')
    res = subprocess.run(['python', script], capture_output=True, text=True)
    if res.returncode != 0:
        print(f'Error in {script}: {res.stderr}')
    else:
        print(f'Success: {script}')
