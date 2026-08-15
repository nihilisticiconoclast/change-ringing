#!/usr/bin/env python3
import json
import subprocess
import urllib.request

def main():
    p = subprocess.Popen(['git', 'credential', 'fill'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate('protocol=https\nhost=github.com\n\n')
    token = None
    for line in out.splitlines():
        if line.startswith('password='):
            token = line.split('=', 1)[1]
            break

    headers = {
        'Authorization': 'token ' + token,
        'User-Agent': 'change-ringing-agent',
        'Accept': 'application/vnd.github.v3+json'
    }

    # Fetch PRs
    req_prs = urllib.request.Request('https://api.github.com/repos/nihilisticiconoclast/change-ringing/pulls?state=all', headers=headers)
    with urllib.request.urlopen(req_prs) as resp:
        prs = json.loads(resp.read().decode('utf-8'))

    print("=== ALL PULL REQUESTS ===")
    for pr in prs:
        num = pr['number']
        state = pr['state']
        title = pr['title']
        head = pr['head']['ref']
        merged_at = pr.get('merged_at')
        print(f"PR #{num:02d} [{state:6s}] (branch: {head:<40s}) -> Merged: {bool(merged_at)} | Title: {title}")

    # Fetch Branches
    req_branches = urllib.request.Request('https://api.github.com/repos/nihilisticiconoclast/change-ringing/branches', headers=headers)
    with urllib.request.urlopen(req_branches) as resp:
        branches = json.loads(resp.read().decode('utf-8'))

    print("\n=== ALL REMOTE BRANCHES ===")
    for b in branches:
        name = b['name']
        sha = b['commit']['sha'][:8]
        print(f"Branch: {name:<45s} SHA: {sha}")

if __name__ == "__main__":
    main()
