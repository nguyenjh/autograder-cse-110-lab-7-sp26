#!/usr/bin/env python3

import json
import subprocess
import sys
import os
import re
import time
import shutil
from pathlib import Path

# Debug function - writes ONLY to stderr
def debug(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()

def run_command(cmd, cwd=None, timeout=120):
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, 
                               capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1

def clone_repository(submission_path):
    txt_files = [f for f in os.listdir(submission_path) if f.endswith('.txt') and '@' in f]
    
    if not txt_files:
        return True, "No repository link found"
    
    with open(os.path.join(submission_path, txt_files[0]), 'r') as f:
        repo_url = f.read().strip()
    
    debug(f"Cloning repository: {repo_url}")
    stdout, stderr, code = run_command(f"git clone --depth 1 --single-branch {repo_url} student_repo", cwd=submission_path, timeout=60)
    
    if code != 0:
        return False, f"Failed to clone: {stderr}"
    
    repo_path = os.path.join(submission_path, "student_repo")
    for item in os.listdir(repo_path):
        src = os.path.join(repo_path, item)
        dst = os.path.join(submission_path, item)
        if not os.path.exists(dst):
            shutil.move(src, dst)
    os.rmdir(repo_path)
    
    debug("Repository cloned successfully")
    return True, "Success"

def start_local_server(submission_path):
    src_path = Path(submission_path) / "src"
    
    if not src_path.exists():
        debug("No src directory found")
        return None, None
    
    debug(f"Starting local server from {src_path}")
    
    process = subprocess.Popen(
        ["npx", "http-server", str(src_path), "-p", "3000", "-s", "-c-1", "--silent"],
        cwd=submission_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    time.sleep(2)
    return process, "http://localhost:3000"

def update_test_file_url(submission_path, local_url):
    test_file = Path(submission_path) / "__tests__/lab7.test.js"
    
    if not test_file.exists():
        test_candidates = list(Path(submission_path).glob("**/lab7.test.js"))
        if test_candidates:
            test_file = test_candidates[0]
        else:
            return
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    if "localhost" in content:
        return
    
    external_urls = [
        "https://cse110-sp25.github.io/CSE110-Shop/",
        "https://cse110-sp26.github.io/CSE110-Shop/"
    ]
    
    for ext_url in external_urls:
        if ext_url in content:
            content = content.replace(ext_url, local_url)
            with open(test_file, 'w') as f:
                f.write(content)
            debug(f"Updated test file to use {local_url}")
            return

def fix_puppeteer_config(submission_path):
    config_content = '''module.exports = {
  launch: {
    dumpio: false,
    headless: "new",
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
      "--disable-extensions",
      "--disable-background-networking",
      "--disable-default-apps",
      "--disable-sync",
      "--disable-translate",
      "--hide-scrollbars",
      "--metrics-recording-only",
      "--mute-audio",
      "--no-first-run"
    ],
    timeout: 15000,
    protocolTimeout: 15000
  }
};
'''
    config_path = Path(submission_path) / "jest-puppeteer.config.js"
    with open(config_path, 'w') as f:
        f.write(config_content)
    debug("Created jest-puppeteer.config.js")
    
    package_path = Path(submission_path) / "package.json"
    if package_path.exists():
        with open(package_path, 'r') as f:
            try:
                pkg = json.load(f)
            except:
                pkg = {}
        
        if "jest" not in pkg:
            pkg["jest"] = {}
        
        pkg["jest"]["preset"] = "jest-puppeteer"
        pkg["jest"]["testTimeout"] = 30000
        
        if "scripts" not in pkg:
            pkg["scripts"] = {}
        pkg["scripts"]["test"] = "jest --forceExit --maxWorkers=1"
        
        with open(package_path, 'w') as f:
            json.dump(pkg, f, indent=2)
        debug("Updated package.json")

def parse_test_results(output):
    results = {"passed": 0, "failed": 0, "total": 0}
    
    # Look for test results
    test_pattern = r'(PASS|FAIL|✓|✕)\s+(.+?)\s+\((\d+)\s+ms\)'
    for line in output.split('\n'):
        match = re.match(test_pattern, line)
        if match:
            results["total"] += 1
            if match.group(1) == 'PASS' or match.group(1) == '✓':
                results["passed"] += 1
            else:
                results["failed"] += 1
    
    # If no individual tests found, try summary
    if results["total"] == 0:
        summary = re.search(r'Tests:\s+(\d+)\s+passed', output)
        if summary:
            results["passed"] = int(summary.group(1))
            results["total"] = results["passed"]
    
    return results

def check_screenshot(submission_path):
    """Check for screenshot of test results - returns 0.5 if found, 0 if not"""
    screenshot_patterns = [
        "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.PNG", "*.JPG"
    ]
    
    found_screenshots = []
    for pattern in screenshot_patterns:
        found_screenshots.extend(Path(submission_path).glob(pattern))
        # Also check in common locations
        for subdir in ["screenshots", "images", "assets"]:
            subdir_path = Path(submission_path) / subdir
            if subdir_path.exists():
                found_screenshots.extend(subdir_path.glob(pattern))
    
    # Filter out node_modules and .git directories
    filtered_screenshots = []
    for ss in found_screenshots:
        if 'node_modules' not in str(ss) and '.git' not in str(ss):
            filtered_screenshots.append(ss)
    
    if filtered_screenshots:
        debug(f"Screenshot found: {filtered_screenshots[0].name}")
        return 0.5, f"[PASS] Screenshot found: {filtered_screenshots[0].name}"
    else:
        debug("No screenshot found")
        return 0, "[FAIL] No screenshot found - please include screenshot of npm test results"

def check_readme(submission_path):
    readme_path = Path(submission_path) / "README.md"
    
    if not readme_path.exists():
        readme_candidates = list(Path(submission_path).glob("**/README.md"))
        if readme_candidates:
            readme_path = readme_candidates[0]
        else:
            return 0, ["[ERROR] README.md not found"]
    
    with open(readme_path, 'r') as f:
        content = f.read().lower()
    
    score = 0
    feedback = []
    # Each question is worth 0.125 points (0.5 total for 4 questions)
    
    if any(kw in content for kw in ["github action", "push", "ci/cd"]):
        score += 0.125
        feedback.append("[PASS] Q1: Automated testing placement")
    else:
        feedback.append("[FAIL] Q1: Missing")
    
    if "no" in content and ("function" in content or "unit" in content):
        score += 0.125
        feedback.append("[PASS] Q2: E2E testing purpose")
    else:
        feedback.append("[FAIL] Q2: Missing")
    
    if "navigation" in content and "snapshot" in content:
        score += 0.125
        feedback.append("[PASS] Q3: Lighthouse modes")
    else:
        feedback.append("[FAIL] Q3: Missing")
    
    keywords = ["perform", "access", "image", "load", "cache", "defer"]
    matches = sum(1 for kw in keywords if kw in content)
    if matches >= 2:
        score += 0.125
        feedback.append(f"[PASS] Q4: Lighthouse improvements (found {matches}/3)")
    else:
        feedback.append("[FAIL] Q4: Missing")
    
    return score, feedback

def main():
    start_time = time.time()
    submission_path = "/autograder/working"
    output_lines = []
    
    # Clone repository
    success, message = clone_repository(submission_path)
    if not success:
        print(json.dumps({"score": 0, "output": message, "tests": []}))
        return
    output_lines.append(message)
    
    # Start local server
    server_process, local_url = start_local_server(submission_path)
    if local_url:
        update_test_file_url(submission_path, local_url)
    
    # Configure
    fix_puppeteer_config(submission_path)
    
    # Check package.json
    if not os.path.exists(os.path.join(submission_path, "package.json")):
        print(json.dumps({"score": 0, "output": "package.json not found", "tests": []}))
        return
    
    # Install dependencies
    debug("Installing dependencies...")
    node_modules_path = Path(submission_path) / "node_modules"
    if node_modules_path.exists():
        debug("Using existing node_modules")
    else:
        run_command("npm install --prefer-offline --no-audit --no-fund", cwd=submission_path, timeout=180)
    
    # Run tests
    debug("Running tests...")
    env = os.environ.copy()
    env['PUPPETEER_EXECUTABLE_PATH'] = '/usr/bin/google-chrome-stable'
    env['NODE_NO_WARNINGS'] = '1'
    
    stdout, stderr, code = run_command("npm test 2>&1", cwd=submission_path, timeout=90)
    debug("Tests completed")
    
    # Parse results - tests are worth 2.0 points
    test_results = parse_test_results(stdout)
    test_score = 0
    if test_results["total"] > 0:
        test_score = (test_results["passed"] / test_results["total"]) * 2.0
    
    # Check README - worth 0.5 points
    readme_score, readme_feedback = check_readme(submission_path)
    
    # Check screenshot - worth 0.5 points
    screenshot_score, screenshot_status = check_screenshot(submission_path)
    
    # Calculate final score (max 3.0)
    final_score = test_score + readme_score + screenshot_score
    final_score = round(min(final_score, 3.0), 2)
    
    # Build output
    elapsed = time.time() - start_time
    output_lines.append(f"\nTest Results (completed in {elapsed:.1f}s):")
    output_lines.append(f"  Total tests: {test_results['total']}")
    output_lines.append(f"  Passed: {test_results['passed']}")
    output_lines.append(f"  Failed: {test_results['failed']}")
    output_lines.append(f"  Test score: {test_score:.2f}/2.00")
    
    output_lines.append("\n" + "=" * 50)
    output_lines.append("README QUESTIONS (0.5 points total)")
    output_lines.append("=" * 50)
    output_lines.extend(readme_feedback)
    output_lines.append(f"\nREADME score: {readme_score:.2f}/0.50")
    
    output_lines.append("\n" + "=" * 50)
    output_lines.append("SCREENSHOT REQUIREMENT (0.5 points)")
    output_lines.append("=" * 50)
    output_lines.append(screenshot_status)
    output_lines.append(f"Screenshot score: {screenshot_score:.2f}/0.50")
    output_lines.append("Note: Screenshot should show npm test results for lab7.test.js")
    
    output_lines.append("\n" + "=" * 50)
    output_lines.append(f"FINAL SCORE: {final_score:.2f}/3.00")
    output_lines.append("=" * 50)
    
    # Cleanup
    if server_process:
        server_process.terminate()
        debug("Server stopped")
    
    # Output JSON
    result = {
        "score": final_score,
        "output": "\n".join(output_lines),
        "tests": []
    }
    print(json.dumps(result))

if __name__ == "__main__":
    main()