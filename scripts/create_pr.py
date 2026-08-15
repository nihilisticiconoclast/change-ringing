#!/usr/bin/env python3
"""
Helper script to create GitHub pull requests using stored git credentials.
"""
import argparse
import json
import subprocess
import urllib.request
import sys

def get_github_token():
    p = subprocess.Popen(['git', 'credential', 'fill'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate('protocol=https\nhost=github.com\n\n')
    for line in out.splitlines():
        if line.startswith('password='):
            return line.split('=', 1)[1]
    return None

def create_pull_request(title, body, head_branch, base_branch="main", repo="nihilisticiconoclast/change-ringing"):
    token = get_github_token()
    if not token:
        print("Error: Could not retrieve GitHub token from git credentials.", file=sys.stderr)
        return None

    # Check if PR already exists
    url_list = f"https://api.github.com/repos/{repo}/pulls?head={repo.split('/')[0]}:{head_branch}"
    req_list = urllib.request.Request(url_list, headers={
        "Authorization": f"token {token}",
        "User-Agent": "change-ringing-agent",
        "Accept": "application/vnd.github.v3+json"
    })
    try:
        with urllib.request.urlopen(req_list) as resp:
            existing = json.loads(resp.read().decode('utf-8'))
            if existing:
                pr = existing[0]
                print(f"Existing Pull Request found: PR #{pr['number']} - {pr['html_url']}")
                return pr['html_url']
    except Exception as e:
        print(f"Warning checking existing PRs: {e}", file=sys.stderr)

    # Create PR
    url_create = f"https://api.github.com/repos/{repo}/pulls"
    payload = json.dumps({
        "title": title,
        "body": body,
        "head": head_branch,
        "base": base_branch
    }).encode('utf-8')

    req_create = urllib.request.Request(url_create, data=payload, headers={
        "Authorization": f"token {token}",
        "User-Agent": "change-ringing-agent",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req_create) as resp:
            pr = json.loads(resp.read().decode('utf-8'))
            print(f"Successfully created Pull Request: PR #{pr['number']}")
            print(f"URL: {pr['html_url']}")
            return pr['html_url']
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8')
        print(f"HTTP Error creating PR ({e.code}): {err_msg}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error creating PR: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a GitHub Pull Request")
    parser.add_argument("--title", required=True, help="PR Title")
    parser.add_argument("--body", required=True, help="PR Body")
    parser.add_argument("--head", required=True, help="Head branch")
    parser.add_argument("--base", default="main", help="Base branch")
    parser.add_argument("--repo", default="nihilisticiconoclast/change-ringing", help="GitHub repo")
    args = parser.parse_args()

    pr_url = create_pull_request(args.title, args.body, args.head, args.base, args.repo)
    if pr_url:
        print(f"PR_URL={pr_url}")
    else:
        sys.exit(1)
