# 🤖 Daily Standup Update Generator

An automated Python script that extracts your daily Git commits, generates AI-powered work summaries using Ollama, and sends professional standup updates to Slack via email.

## ✨ Features

- **Git Integration**: Automatically fetches all commits from today
- **Full Commit Messages**: Captures complete multi-line commit descriptions
- **AI-Powered Summaries**: Uses Ollama (llama3.2) to generate concise work summaries
- **Slack Integration**: Sends formatted updates directly to Slack channels via email
- **File Logging**: Saves daily reports as timestamped text files
- **Environment Variables**: Secure credential management
- **Automated Scheduling**: Set up daily execution at 6:00 PM

## 🛠️ Prerequisites

- Python 3.6+
- Git repository with commits
- Ollama installed and running locally
- Gmail account with 2FA and app password
- Slack email integration enabled

## 📦 Installation

1. **Clone/Download the script**

```bash
git clone <your-repo-url>
cd daily-standup-update
```

2. **Install Ollama and pull model**

```bash
# Install Ollama (macOS)
brew install ollama

# Pull the model
ollama pull llama3.2:latest

# Start Ollama service
ollama serve
```

3. **Set up Gmail App Password**

   - Enable 2FA on Gmail
   - Generate app password: Google Account → Security → 2-Step Verification → App passwords
   - Select "Mail" and copy the 16-character password

4. **Configure environment variables**
   Create `.env` file:

```env
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_16_char_app_password
SLACK_EMAIL=your_slack_email@company.slack.com
REPO_PATH=/path/to/your/repository
OLLAMA_MODEL=llama3.2:latest
```

## 🚀 Usage

**Manual execution:**

```bash
python3 main.py
```

**Automated daily scheduling:**

```bash
# Add to crontab for daily 6 PM execution
crontab -e
# Add: 0 18 * * * /usr/bin/python3 /path/to/main.py
```

## 📝 Sample Output

```
📊 Commits Made: 5

📋 Work Summary:
Today's work focused on implementing user authentication features and fixing critical bugs. Key accomplishments include completing the OAuth integration with Google, resolving database connection issues, and enhancing the frontend user interface. Additional progress was made on API documentation and code refactoring for better maintainability.
```

## 🏗️ How It Works

1. **Extracts Commits**: Scans Git repository for today's commits with full messages
2. **AI Analysis**: Sends commit data to local Ollama instance for summary generation
3. **Email Delivery**: Formats and sends professional summary to Slack channel
4. **File Storage**: Saves detailed log with commits and summary as `commits_DD-MM-YY.txt`

## 🔧 Configuration

**Customize the prompt** in `get_ollama_summary()` to match your team's standup format.

**Different Ollama models** can be specified in the `.env` file.

**Repository path** can be set to `None` to use current directory.

## 🤝 Benefits

- **Consistency**: Never miss standup updates again
- **Professional**: AI-generated summaries sound polished and concise
- **Time-Saving**: Automates the tedious task of writing daily updates
- **Historical Record**: Maintains searchable archive of daily progress
- **Team Transparency**: Automatic sharing keeps everyone informed

---

_Streamline your daily standups with AI-powered automation! 🚀_

## 🔗 Connect

Found this useful? Let's connect on [LinkedIn](https://www.linkedin.com/in/r-vigneshwaran/) and discuss more automation ideas!
