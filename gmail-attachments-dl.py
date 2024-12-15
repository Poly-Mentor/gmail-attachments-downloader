import os
import base64
import pickle
import email
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    """Get authenticated Gmail API service instance."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def download_attachment(service, message_id, attachment_id, filename):
    """Download a specific attachment."""
    attachment = service.users().messages().attachments().get(
        userId='me', messageId=message_id, id=attachment_id
    ).execute()

    file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))

    # Create 'downloads' directory if it doesn't exist
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    filepath = os.path.join('downloads', filename)
    with open(filepath, 'wb') as f:
        f.write(file_data)

    return filepath

def get_attachments(service, message_id):
    """Get list of attachments for a specific email."""
    message = service.users().messages().get(userId='me', id=message_id).execute()
    parts = message.get('payload', {}).get('parts', [])
    attachments = []

    for part in parts:
        if part.get('filename') and part.get('body', {}).get('attachmentId'):
            attachments.append({
                'id': part['body']['attachmentId'],
                'filename': part['filename'],
                'mimeType': part['mimeType']
            })

    return attachments

def download_attachments_from_selected_emails(service, topic='saveit', unread_only=True):
    """Download attachments from emails matching the topic."""
    query = f'subject:{topic}'
    if unread_only:
        query += ' is:unread'

    # Search for messages
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    # Download attachments from each message
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        attachments = get_attachments(service, message['id'])

        for attachment in attachments:
            filepath = download_attachment(
                service,
                message['id'],
                attachment['id'],
                attachment['filename']
            )
            print(f"Downloaded {attachment['filename']} to {filepath}")

        # Mark message as read
        service.users().messages().modify(
            userId='me', id=message['id'],
            body={
                'removeLabelIds': ['UNREAD']
            }
        ).execute()

    print('All matching attachments downloaded.')

if __name__ == '__main__':
    service = get_gmail_service()
    download_attachments_from_selected_emails(service)
