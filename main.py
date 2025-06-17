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

def get_commits_by_date(repo_path=None, date=None):
    """Get all commit messages for a specific date from a Git repository."""
    if repo_path:
        os.chdir(repo_path)
    
    if date is None:
        date = datetime.date.today().strftime('%Y-%m-%d')
    
    try:
        cmd = [
            'git', 'log', 
            '--since', f'{date} 00:00:00',
            '--until', f'{date} 23:59:59',
            '--pretty=format:COMMIT_START%H|%an|%ad%nCOMMIT_MESSAGE_START%B%nCOMMIT_END',
            '--date=short'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if not result.stdout.strip():
            print(f"No commits found for {date}")
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
                    'message': message
                })
        
        return commits
        
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}")
        return []
    except FileNotFoundError:
        print("Git not found. Please ensure Git is installed and in PATH.")
        return []

def get_ollama_summary(commit_messages, env_vars):
    """Send commit messages to Ollama and get work summary."""
    if not commit_messages:
        return "No commits found for today."
    
    combined_messages = "\n\n".join([f"- {msg}" for msg in commit_messages])
    
    prompt = f"""Based on these git commit messages from today, provide a concise summary of the work accomplished:

{combined_messages}

Please provide a brief, professional summary suitable for a daily standup meeting."""
    
    try:
        cmd = [
            'curl', '-s', '-X', 'POST', 'http://localhost:11434/api/generate',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                "model": env_vars.get('OLLAMA_MODEL', 'llama3.2:latest'),
                "prompt": prompt,
                "stream": False
            })
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        response = json.loads(result.stdout)
        
        return response.get('response', 'No response from Ollama')
        
    except Exception as e:
        return f"Error with Ollama: {e}"

def send_email(summary, commits_count, env_vars):
    """Send work summary to Slack email."""
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
        
        body = f"""Daily Work Summary for {datetime.date.today().strftime('%d/%m/%Y')}

📊 Commits Made: {commits_count}

📋 Work Summary:
{summary}

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
    REPO_PATH = env_vars.get('REPO_PATH')
    
    print(f"Fetching commits for {datetime.date.today()}")
    
    commits = get_commits_by_date(REPO_PATH)
    commit_messages = []
    
    if commits:
        print(f"\nFound {len(commits)} commit(s):")
        print("-" * 80)
        
        for commit in commits:
            print(f"Hash: {commit['hash']}")
            print(f"Author: {commit['author']}")
            print(f"Date: {commit['date']}")
            print(f"Message: {commit['message']}")
            print("-" * 80)
            commit_messages.append(commit['message'])
        
        print("\nGenerating work summary with Ollama...")
        summary = get_ollama_summary(commit_messages, env_vars)
        print(f"\n📋 Today's Work Summary:\n{summary}")
        
        send_email(summary, len(commits), env_vars)
        
    else:
        summary = "No commits found for today."
        send_email(summary, 0, env_vars)
    
    # Save to file
    log_file = f"commits_{datetime.date.today().strftime('%d-%m-%y')}.txt"
    
    try:
        with open(log_file, 'w') as f:
            f.write(f"Commits for {datetime.date.today()}\n")
            f.write("=" * 50 + "\n\n")
            
            if commits:
                for commit in commits:
                    f.write(f"Hash: {commit['hash']}\n")
                    f.write(f"Author: {commit['author']}\n")
                    f.write(f"Date: {commit['date']}\n")
                    f.write(f"Message: {commit['message']}\n")
                    f.write("-" * 40 + "\n")
            else:
                f.write("No commits found for this date.\n")
            
            f.write(f"\n📋 AI Summary:\n{summary}\n")

        print(f"\nResults saved to: {log_file}")
        
    except IOError as e:
        print(f"Error creating/writing file {log_file}: {e}")
        print(f"Current directory: {os.getcwd()}")
        sys.exit(1)

if __name__ == "__main__":
    main()