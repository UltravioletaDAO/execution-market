# Store Assets

## Deep Link Verification Files

These files must be hosted on `execution.market` at `/.well-known/` for deep links (Universal Links on iOS, App Links on Android) to work.

### `well-known/apple-app-site-association`

- Served at `https://execution.market/.well-known/apple-app-site-association`
- Must be served with `Content-Type: application/json` (no file extension)
- **Replace `TEAM_ID`** with the actual Apple Developer Team ID before deploying

### `well-known/assetlinks.json`

- Served at `https://execution.market/.well-known/assetlinks.json`
- **Replace `FINGERPRINT_PLACEHOLDER`** with the SHA-256 certificate fingerprint from Play App Signing
- To get the fingerprint: Google Play Console > App > Setup > App signing > SHA-256 certificate fingerprint

### Deployment

Copy both files to the web server or CDN serving `execution.market`:

```bash
# If using S3 + CloudFront (current infra):
aws s3 cp well-known/apple-app-site-association s3://BUCKET/.well-known/apple-app-site-association --content-type application/json
aws s3 cp well-known/assetlinks.json s3://BUCKET/.well-known/assetlinks.json --content-type application/json
```

Both files must be accessible without authentication (public).
