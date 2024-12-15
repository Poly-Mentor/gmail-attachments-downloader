import os
import base64
import pickle
import email
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import argparse

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    """Get authenticated Gmail API service instance."""
    creds = None
    creds_path = os.path.join(args.credentials_folder, 'credentials.json')
    token_path = os.path.join(args.credentials_folder, 'token.pickle')

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def download_attachment(service, message_id, attachment_id, filename, target_path, overwrite=False):
    """Download a specific attachment."""
    attachment = service.users().messages().attachments().get(
        userId='me', messageId=message_id, id=attachment_id
    ).execute()

    file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))

    filepath = os.path.join(target_path, filename)
    if os.path.exists(filepath) and not overwrite:
        print(f"File {filepath} already exists. Use --overwrite to overwrite.")
        return None

    if not os.path.exists(target_path):
        os.makedirs(target_path)

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

def download_attachments_from_selected_emails(service, topic='saveit', unread_only=True, target_path='downloads', overwrite=False):
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
                attachment['filename'],
                target_path,
                overwrite
            )
            if filepath:
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
    parser = argparse.ArgumentParser(description='Download Gmail attachments based on topic.')
    parser.add_argument('--topic', default='saveit', help='Topic to search for in emails.')
    parser.add_argument('--unread-only', action='store_true', help='Search only unread emails.')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files.')
    parser.add_argument('-t', '--target-path', default='downloads', help='Target path for downloaded files.')
    parser.add_argument('-c', '--credentials-folder', default='.', help='Path to the folder containing credentials.json and token.pickle.')
    args = parser.parse_args()

    service = get_gmail_service()
    download_attachments_from_selected_emails(service, args.topic, args.unread_only, args.target_path, args.overwrite)
