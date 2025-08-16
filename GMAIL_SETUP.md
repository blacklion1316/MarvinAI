# Gmail API Setup for MARVIN

## 📧 How to Enable Gmail Integration

### Step 1: Google Cloud Console Setup

1. **Go to Google Cloud Console**

    - Visit: https://console.cloud.google.com/

2. **Create or Select Project**

    - Create a new project or select an existing one
    - Name it something like "MARVIN-AI-Assistant"

3. **Enable Gmail API**
    - Go to "APIs & Services" > "Library"
    - Search for "Gmail API"
    - Click on it and press "Enable"

### Step 2: Create OAuth 2.0 Credentials

1. **Configure OAuth Consent Screen**

    - Go to "APIs & Services" > "OAuth consent screen"
    - Choose "External" (unless you have a Google Workspace)
    - Fill in required fields:
        - App name: "MARVIN AI Assistant"
        - User support email: your email
        - Developer contact: your email
    - Add scopes: `../auth/gmail.readonly`, `../auth/gmail.send`, `../auth/gmail.modify`

2. **Create Credentials**

    - Go to "APIs & Services" > "Credentials"
    - Click "Create Credentials" > "OAuth 2.0 Client IDs"
    - Application type: "Desktop application"
    - Name: "MARVIN Gmail Client"
    - Download the JSON file

3. **Save Credentials**
    - Rename the downloaded file to `credentials.json`
    - Place it in your MARVIN project folder (same directory as MARVIN_Local.py)

### Step 3: Test the Integration

1. **Run MARVIN**

    ```bash
    python MARVIN_Local.py
    ```

2. **First Time Setup**

    - MARVIN will open a browser window
    - Sign in to your Google account
    - Grant permissions to MARVIN
    - The browser will show "The authentication flow has completed"

3. **Voice Commands**
    - "Check email" - Read recent emails
    - "Send email" - Compose and send emails
    - "Search email" - Find specific emails

## 🎯 Available Gmail Commands

### Check Recent Emails

**Say:** "Check email" or "Read email"

-   Lists your 5 most recent emails
-   Reads sender, subject, and preview
-   Option to hear full content or AI summary

### Send Email

**Say:** "Send email"

-   Prompts for recipient email address
-   Asks for subject line
-   Dictate your message
-   Confirms before sending

### Search Emails

**Say:** "Search email"

-   Ask what to search for
-   Shows matching emails
-   Reads sender and subject of results

## 🔒 Security & Privacy

-   **Local Processing**: Email content is processed locally with your gpt-oss model
-   **No External AI**: Email content never sent to external AI services
-   **OAuth 2.0**: Secure authentication with Google
-   **Limited Scope**: Only accesses emails with your explicit permission

## 🛠️ Troubleshooting

### "Gmail credentials.json file not found!"

-   Make sure you downloaded and renamed the OAuth credentials file
-   Place it in the same folder as MARVIN_Local.py

### "Failed to authenticate with Gmail"

-   Delete `token.json` if it exists
-   Run MARVIN again to re-authenticate
-   Check that Gmail API is enabled in Google Cloud Console

### "No recent emails found"

-   Check your internet connection
-   Verify Gmail API permissions were granted
-   Try running the authentication flow again

## 📝 Example Usage

1. **Start MARVIN**: `python MARVIN_Local.py`
2. **Check emails**: Say "Check email"
3. **MARVIN responds**: "You have 3 recent emails. Email 1. From john@example.com. Subject: Meeting tomorrow"
4. **You can say**: "Yes, read it" or "Next email"
5. **Send reply**: Say "Send email" and follow prompts

## 🚀 Advanced Features

-   **AI Email Summaries**: Long emails are automatically summarized
-   **Smart Threading**: Replies maintain email conversation threads
-   **Voice Control**: Everything controlled by voice commands
-   **Privacy First**: All AI processing happens locally on your machine
