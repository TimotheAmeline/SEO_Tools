# GSC Analyzer Setup Guide

## Option 1: Using a Service Account (Recommended for automation)

If you already have a service account with access to your Search Console property, this is the preferred method.

### Step 1: Prepare your service account key file
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "IAM & Admin" > "Service Accounts"
3. Find your service account and click on the three dots menu
4. Select "Manage keys"
5. Click "ADD KEY" > "Create new key"
6. Choose JSON as the key type and click "CREATE"
7. The key file will be downloaded to your computer
8. Rename the file to `service_account.json` and place it in the root directory of this project

### Step 2: Verify permissions
- Make sure the service account has owner-level access to your Search Console property
- The service account email should be added directly to your Search Console property with "Owner" permissions

### Step 3: Update Configuration
1. Open the `config.py` file
2. Set `USE_SERVICE_ACCOUNT = True`
3. Update the `SITE_URL` value with your actual Search Console property URL:
   ```python
   SITE_URL = 'https://www.yourwebsite.com/'  # Include the protocol (https://) and trailing slash