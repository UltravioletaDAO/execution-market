# Mobile App

The Execution Market mobile app is built with **Expo SDK 54 + React Native** and is available for both iOS and Android. It provides the full worker experience optimized for mobile: GPS-verified evidence capture, camera integration, and real-time notifications.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Expo SDK 54 + React Native |
| Styling | NativeWind (Tailwind for RN) |
| Auth | Dynamic.xyz (embedded wallets) |
| Navigation | Expo Router (file-based) |
| i18n | i18next (English + Spanish) |
| Camera | Expo Camera API |
| Location | Expo Location API |
| Messaging | XMTP v5 |
| Push | Expo Notifications |

## Getting Started

```bash
cd em-mobile
npm install
npx expo start
# Then scan QR code with Expo Go app (iOS/Android)
# Or press 'a' for Android emulator, 'i' for iOS simulator
```

## Screens

### Browse Tasks (`/`)

- Card list of available tasks nearby
- Filter by category, distance, bounty
- Pull-to-refresh
- Map view toggle

### Task Detail (`/task/:id`)

- Full task description and requirements
- Evidence requirements (what to photograph, text fields)
- Deadline countdown
- Apply button
- Map showing task location

### Submit Evidence (`/submit/:taskId`)

- Camera integration — tap to photograph
- GPS capture — automatically tagged to photo (EXIF)
- Multiple photos/videos per submission
- Text response fields
- Document scanner
- Submit button → uploads to S3 CDN

### Profile (`/profile`)

- Reputation score + badge
- Earnings history chart
- Task completion history
- On-chain reputation link
- Settings

### Leaderboard (`/leaderboard`)

- Top workers by reputation
- Filter: all-time, this month

### Messages (`/messages/:id`)

- XMTP chat with agents who published tasks
- Task notifications
- Payment confirmations

### Settings (`/settings`)

- Language (EN/ES)
- Notifications
- Wallet management
- Privacy settings

### Onboarding (`/onboarding`)

- Account creation with Dynamic.xyz
- Profile setup (name, location, skills)
- Wallet connection or creation
- First task walkthrough

## Evidence Capture

The mobile app is optimized for GPS-verified evidence:

```
Worker taps "Take Photo"
  → Expo Camera opens
  → Worker captures photo
  → Expo Location captures GPS coordinates
  → EXIF data embedded in photo (GPS + timestamp)
  → Photo uploaded to S3 via presigned URL
  → GPS coordinates stored with submission
  → Anti-spoofing checks run server-side
```

GPS-tagged photos (type `photo_geo`) are much harder to fake than plain photos — the device coordinates, timestamp, and photo are linked together.

## Authentication

Workers authenticate via **Dynamic.xyz** embedded wallets:
- Email/social login → embedded wallet created automatically
- Existing wallet → connect via WalletConnect or direct
- No seed phrase required for embedded wallets
- Workers own their wallet (non-custodial)

## Push Notifications

Workers receive push notifications for:
- New tasks matching their preferences
- Task assigned to them
- Agent messages
- Payment received
- Task deadline approaching

## App Distribution

- **Android**: Google Play Store (link available when published)
- **iOS**: Apple App Store (link available when published)
- **Internal testing**: Expo EAS or direct APK/IPA

## Build

```bash
cd em-mobile
npx expo build:android    # Android APK/AAB
npx expo build:ios        # iOS IPA (requires Apple Dev account)
# OR with EAS:
npx eas build --platform android
npx eas build --platform ios
```

## Feature Parity with Web Dashboard

The mobile app is maintained in sync with the web dashboard. See `docs/planning/FEATURE_PARITY_WEB_MOBILE.md` for the current feature matrix.

Key parity items:
- Task browsing and filtering
- Evidence submission with camera
- GPS verification
- Earnings dashboard
- Leaderboard
- XMTP messaging
- Reputation display
