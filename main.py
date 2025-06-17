#!/usr/bin/env python3
import subprocess
import datetime
import os
import sys
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def load_env():
    """Load environment variables from .env file"""
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    except FileNotFoundError:
        print("Error: .env file not found. Please create it with required variables.")
        sys.exit(1)
    return env_vars

def get_commits_by_date(repo_path=None, repo_name="Repository", date=None):
    """Get all commit messages for a specific date from a Git repository."""
    original_dir = os.getcwd()
    
    try:
        if repo_path:
            os.chdir(repo_path)
        
        if date is None:
            date = datetime.date.today().strftime('%Y-%m-%d')
        
        cmd = [
            'git', 'log', 
            '--since', f'{date} 00:00:00',
            '--until', f'{date} 23:59:59',
            '--pretty=format:COMMIT_START%H|%an|%ad%nCOMMIT_MESSAGE_START%B%nCOMMIT_END',
            '--date=short'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if not result.stdout.strip():
            print(f"No commits found for {repo_name} on {date}")
            return []
        
        commits = []
        commit_blocks = result.stdout.strip().split('COMMIT_START')[1:]
        
        for block in commit_blocks:
            if block.strip():
                lines = block.strip().split('\n')
                header = lines[0]
                hash_val, author, commit_date = header.split('|', 2)
                
                message_start = block.find('COMMIT_MESSAGE_START') + len('COMMIT_MESSAGE_START')
                message_end = block.find('COMMIT_END')
                message = block[message_start:message_end].strip()
                
                commits.append({
                    'hash': hash_val[:8],
                    'author': author,
                    'date': commit_date,
                    'message': message,
                    'repo': repo_name
                })
        
        return commits
        
    except subprocess.CalledProcessError as e:
        print(f"Error running git command for {repo_name}: {e}")
        return []
    except FileNotFoundError:
        print(f"Git not found for {repo_name}. Please ensure Git is installed and in PATH.")
        return []
    finally:
        os.chdir(original_dir)

def get_ollama_summary(project_commits, env_vars):
    """Generate AI summary for multiple projects."""
    if not project_commits:
        return "No commits found for today.", {}
    
    # Build prompt with project sections
    prompt_sections = []
    for project_name, commits in project_commits.items():
        if commits:
            commit_list = "\n".join([f"  - {commit['message']}" for commit in commits])
            prompt_sections.append(f"{project_name} ({len(commits)} commits):\n{commit_list}")
    
    if not prompt_sections:
        return "No commits found across all projects today.", {}
    
    # Get concise summary
    concise_prompt = f"""Based on these git commits from multiple projects today, provide a brief professional summary suitable for a daily standup meeting:

{chr(10).join(prompt_sections)}

Keep it concise and professional."""
    
    # Get bullet points for each project
    bullet_prompt = f"""Based on these git commits, create a short bullet-point list for each project showing key accomplishments:

{chr(10).join(prompt_sections)}

Format as:
Project Name:
• Key point 1
• Key point 2"""
    
    try:
        # Get concise summary
        cmd1 = [
            'curl', '-s', '-X', 'POST', 'http://localhost:11434/api/generate',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                "model": env_vars.get('OLLAMA_MODEL', 'llama3.2:latest'),
                "prompt": concise_prompt,
                "stream": False
            })
        ]
        
        result1 = subprocess.run(cmd1, capture_output=True, text=True, check=True)
        response1 = json.loads(result1.stdout)
        concise_summary = response1.get('response', 'No response from Ollama')
        
        # Get bullet points
        cmd2 = [
            'curl', '-s', '-X', 'POST', 'http://localhost:11434/api/generate',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                "model": env_vars.get('OLLAMA_MODEL', 'llama3.2:latest'),
                "prompt": bullet_prompt,
                "stream": False
            })
        ]
        
        result2 = subprocess.run(cmd2, capture_output=True, text=True, check=True)
        response2 = json.loads(result2.stdout)
        bullet_points = response2.get('response', 'No bullet points generated')
        
        return concise_summary, bullet_points
        
    except Exception as e:
        return f"Error with Ollama: {e}", ""

def send_email(project_summaries, total_commits, concise_summary, bullet_points, env_vars):
    """Send multi-project work summary to Slack email."""
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = env_vars.get('SENDER_EMAIL')
        sender_password = env_vars.get('SENDER_PASSWORD')
        recipient_email = env_vars.get('SLACK_EMAIL')
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Daily Work Summary - {datetime.date.today().strftime('%d/%m/%Y')}"
        
        # Build project breakdown
        project_breakdown = ""
        for project, commits in project_summaries.items():
            project_breakdown += f"📁 {project}: {len(commits)} commits\n"
        
        body = f"""Daily Work Summary for {datetime.date.today().strftime('%d/%m/%Y')}

📊 Total Commits: {total_commits}

{project_breakdown}

📝 Concise Summary:
{concise_summary}

📋 Project Breakdown:
{bullet_points}

---
Generated automatically by daily standup script
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        
        print(f"✅ Summary sent to Slack email")
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")

def main():
    env_vars = load_env()
    
    # Parse multiple repositories
    repo_paths = env_vars.get('REPO_PATHS', '').split(',')
    repo_names = env_vars.get('REPO_NAMES', '').split(',')
    
    if len(repo_paths) != len(repo_names):
        print("Error: REPO_PATHS and REPO_NAMES must have same number of entries")
        sys.exit(1)
    
    print(f"Fetching commits for {datetime.date.today()} across {len(repo_paths)} projects")
    
    all_commits = []
    project_commits = {}
    
    # Process each repository
    for repo_path, repo_name in zip(repo_paths, repo_names):
        repo_path = repo_path.strip()
        repo_name = repo_name.strip()
        
        print(f"\n🔍 Checking {repo_name}...")
        commits = get_commits_by_date(repo_path, repo_name)
        
        if commits:
            print(f"Found {len(commits)} commit(s) in {repo_name}")
            project_commits[repo_name] = commits
            all_commits.extend(commits)
        else:
            project_commits[repo_name] = []
    
    # Display results by project
    total_commits = len(all_commits)
    print(f"\n📊 Total commits across all projects: {total_commits}")
    
    for project_name, commits in project_commits.items():
        if commits:
            print(f"\n📁 {project_name} ({len(commits)} commits):")
            print("-" * 60)
            for commit in commits:
                print(f"Hash: {commit['hash']}")
                print(f"Author: {commit['author']}")
                print(f"Date: {commit['date']}")
                print(f"Message: {commit['message']}")
                print("-" * 60)
    
    # Generate AI summaries
    if total_commits > 0:
        print("\n🤖 Generating work summaries with Ollama...")
        concise_summary, bullet_points = get_ollama_summary(project_commits, env_vars)
        
        print(f"\n📝 Concise Summary:\n{concise_summary}")
        print(f"\n📋 Project Breakdown:\n{bullet_points}")
        
        send_email(project_commits, total_commits, concise_summary, bullet_points, env_vars)
    else:
        concise_summary = "No commits found across all projects today."
        bullet_points = ""
        send_email(project_commits, 0, concise_summary, bullet_points, env_vars)
    
    # Save to file
    log_file = f"commits_{datetime.date.today().strftime('%d-%m-%y')}.txt"
    
    try:
        with open(log_file, 'w') as f:
            f.write(f"Multi-Project Commits for {datetime.date.today()}\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"📊 Total Commits: {total_commits}\n\n")
            
            for project_name, commits in project_commits.items():
                f.write(f"📁 {project_name} ({len(commits)} commits)\n")
                f.write("-" * 50 + "\n")
                
                if commits:
                    for commit in commits:
                        f.write(f"Hash: {commit['hash']}\n")
                        f.write(f"Author: {commit['author']}\n")
                        f.write(f"Date: {commit['date']}\n")
                        f.write(f"Message: {commit['message']}\n")
                        f.write("-" * 30 + "\n")
                else:
                    f.write("No commits found.\n")
                
                f.write("\n")
            
            f.write(f"📝 Concise Summary:\n{concise_summary}\n\n")
            f.write(f"📋 Project Breakdown:\n{bullet_points}\n")

        print(f"\n💾 Results saved to: {log_file}")
        
    except IOError as e:
        print(f"❌ Error creating/writing file {log_file}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()