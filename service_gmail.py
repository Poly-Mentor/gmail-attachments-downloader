import os
import base64
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify',
          'https://mail.google.com/']  # Full access to Gmail account, including deletion

class GmailService:
    def __init__(self, credentials_folder='.'):
        self.credentials_folder = credentials_folder
        self.service = self._get_gmail_service()

    def _get_gmail_service(self):
        """Get authenticated Gmail API service instance."""
        creds = None
        creds_path = os.path.join(self.credentials_folder, 'credentials.json')
        token_path = os.path.join(self.credentials_folder, 'token.pickle')

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

    def download_attachment(self, message_id, attachment_id, filename, target_path, overwrite=False):
        """Download a specific attachment."""
        attachment = self.service.users().messages().attachments().get(
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

    def get_attachments(self, message_id):
        """Get list of attachments for a specific email."""
        message = self.service.users().messages().get(userId='me', id=message_id).execute()
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

    def delete_message(self, message_id):
        """Delete a message permanently."""
        try:
            self.service.users().messages().delete(userId='me', id=message_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting message {message_id}: {str(e)}")
            return False

    def download_attachments_from_selected_emails(self, topic='saveit', unread_only=True, target_path='downloads', overwrite=False, delete_after=False):
        """Download attachments from emails matching the topic."""
        query = f'subject:{topic}'
        if unread_only:
            query += ' is:unread'

        # Search for messages
        results = self.service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])

        if not messages:
            print(f"No messages found matching the topic: {topic}")
            return

        # Download attachments from each message
        for message in messages:
            msg = self.service.users().messages().get(userId='me', id=message['id']).execute()
            attachments = self.get_attachments(message['id'])
            
            # Track if all attachments were downloaded successfully
            all_attachments_downloaded = True
            
            for attachment in attachments:
                filepath = self.download_attachment(
                    message['id'],
                    attachment['id'],
                    attachment['filename'],
                    target_path,
                    overwrite
                )
                if filepath:
                    print(f"Downloaded {attachment['filename']} to {filepath}")
                else:
                    all_attachments_downloaded = False

            # Delete message if requested and all attachments were downloaded
            if delete_after and all_attachments_downloaded:
                if self.delete_message(message['id']):
                    print(f"Message deleted successfully")
            else:
                # Mark message as read if not deleting
                self.service.users().messages().modify(
                    userId='me', id=message['id'],
                    body={
                        'removeLabelIds': ['UNREAD']
                    }
                ).execute()

        print('All matching attachments downloaded.')
