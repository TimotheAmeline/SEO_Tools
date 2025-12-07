import json
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import argparse
import os

# Path to your JSON credentials file
SERVICE_ACCOUNT_FILE = 'SEOTools/gsc-analyzer/service_account.json'

# URLs to request indexing for (from a file or list)
urls_to_index = ["https://www.example.com/page1"]

# Rate limits: max 200 URLs per day, max 600 URLs per month
# Create credentials
def run_indexing(credentials_path: str, urls: list):
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=['https://www.googleapis.com/auth/indexing']
    )

    service = build('indexing', 'v3', credentials=credentials)

    successful = 0
    failed = 0
    errors = []

    for url in urls:
        try:
            service.urlNotifications().publish(
                body={'url': url, 'type': 'URL_UPDATED'}
            ).execute()

            successful += 1
            print(f"Successfully submitted {url}")

            time.sleep(2)

        except HttpError as error:
            failed += 1
            error_details = json.loads(error.content.decode())
            errors.append({'url': url, 'error': error_details})
            print(f"Error submitting {url}: {error}")

    print(f"\nIndexing complete. Successfully submitted: {successful}, Failed: {failed}")
    if failed > 0:
        print("Errors encountered:")
        for err in errors:
            print(f"URL: {err['url']}, Error: {err['error']}")


def main():
    parser = argparse.ArgumentParser(description='Submit URLs to Google Indexing API')
    parser.add_argument('--credentials', default=SERVICE_ACCOUNT_FILE, help='Path to service account JSON')
    parser.add_argument('--urls-file', help='File containing URLs to index (one per line)')
    args = parser.parse_args()

    urls = urls_to_index
    if args.urls_file and os.path.exists(args.urls_file):
        with open(args.urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]

    run_indexing(args.credentials, urls)


if __name__ == '__main__':
    main()
