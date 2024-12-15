import argparse
from service_gmail import GmailService

def main():
    parser = argparse.ArgumentParser(description='Download Gmail attachments based on topic.')
    parser.add_argument('--topic', default='saveit', help='Topic to search for in emails.')
    parser.add_argument('--unread-only', action='store_true', help='Search only unread emails.')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files.')
    parser.add_argument('-t', '--target-path', default='downloads', help='Target path for downloaded files.')
    parser.add_argument('-c', '--credentials-folder', default='.', help='Path to the folder containing credentials.json and token.pickle.')
    parser.add_argument('-d', '--delete', action='store_true', help='Delete emails after successful attachment download.')
    args = parser.parse_args()

    # Initialize Gmail service
    gmail_service = GmailService(credentials_folder=args.credentials_folder)
    
    # Download attachments
    gmail_service.download_attachments_from_selected_emails(
        topic=args.topic,
        unread_only=args.unread_only,
        target_path=args.target_path,
        overwrite=args.overwrite,
        delete_after=args.delete
    )

if __name__ == '__main__':
    main()
