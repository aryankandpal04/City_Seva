# How to Fix Google Maps API RefererNotAllowedMapError

You need to configure your Google Maps API key to allow requests from your development environment.

## Steps to Fix:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to APIs & Services > Credentials
4. Find your API key and click on it to edit
5. Under "Application restrictions", make sure you have "HTTP referrers" selected
6. Under "Website restrictions", add the following URLs:
   - `http://192.168.136.200:5000/*`
   - `http://localhost:5000/*`
   - Any other domains or IPs where you'll be testing

7. Click "Save" to apply the changes

## Note:
- Changes might take a few minutes to propagate
- For production, make sure to restrict your API key properly to only your production domains
- Alternatively, you can temporarily set the restriction to "None" for testing, but remember to set proper restrictions before going to production 