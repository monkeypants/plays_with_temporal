# Google Calendar API Setup

This guide walks you through setting up Google Calendar API access for the calendar integration demo.

## Prerequisites

- A Google account with Google Calendar access
- Python environment with the calendar package dependencies installed

## Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project ID for later use

## Step 2: Enable the Google Calendar API

1. In the Google Cloud Console, navigate to "APIs & Services" > "Library"
2. Search for "Google Calendar API"
3. Click on it and press "Enable"

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type (unless you have a Google Workspace account)
   - Fill in the required fields (app name, user support email, developer contact)
   - Add your email to test users
4. For application type, choose "Desktop application"
5. Give it a name (e.g., "Calendar Triage Demo")
6. Click "Create"

## Step 4: Download Credentials

1. After creating the OAuth client, click the download button (⬇️) next to your credential
2. Save the downloaded file as `credentials.json` in the same directory as `demo_google.py`
3. Verify the file structure matches `credentials.json.example`

## Step 5: Install Dependencies

Make sure you have the required Google API dependencies:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Step 6: Run the Demo

```bash
# Make the script executable first
chmod +x bin/run-google-calendar-demo

# Run the demo via the wrapper script
./bin/run-google-calendar-demo
```

Alternatively, you can run the Python script directly:
```bash
python cal/cli/google_calendar.py
```

On first run:
1. A browser window will open asking you to sign in to Google
2. Grant permission to access your calendar
3. The demo will create a `token.json` file to store your access token
4. Subsequent runs will use the stored token

## Troubleshooting

### "credentials.json not found"
- Ensure you've downloaded the credentials file and placed it in the correct location
- Check that the filename is exactly `credentials.json` (not `credentials (1).json` or similar)

### "Access blocked: This app's request is invalid"
- Make sure you've enabled the Google Calendar API for your project
- Verify your OAuth consent screen is properly configured
- Check that your email is added as a test user

### "Token has been expired or revoked"
- Delete the `token.json` file and run the demo again
- This will trigger a new OAuth flow

### "No calendar events found"
- The demo looks for events in today's date range
- Add some events to your Google Calendar and try again
- Check that you're using the correct calendar (the demo uses your primary calendar)

### Permission Errors
- Ensure the demo has read access to your calendar
- Check the OAuth scopes in the consent screen

## Security Notes

- Keep your `credentials.json` file secure and never commit it to version control
- The `token.json` file contains your access token - treat it as sensitive data
- For production use, consider using service account credentials instead of OAuth

## API Limits

- Google Calendar API has usage limits (requests per day, per minute, per user)
- For development and testing, the default limits should be sufficient
- Monitor your usage in the Google Cloud Console if needed

## Next Steps

Once the demo is working:
- Explore the triage decisions made by the AI
- Modify the classifier logic in `LocalTimeBlockClassifierRepository`
- Integrate with your existing productivity workflows
- Consider implementing calendar write operations for more advanced features
