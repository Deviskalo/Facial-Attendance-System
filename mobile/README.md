# Face Attendance mobile app

The Expo app is a read-only Android/iOS companion for the existing attendance host. The server remains the source of truth; the app does not enroll faces, recognize faces, edit people, or change attendance.

## Requirements

- Node.js and npm.
- The project dependencies installed with `npm install` from this directory.
- An Expo-compatible Android device/emulator or iOS device/simulator.
- A trusted HTTPS address for the attendance host. The mobile app intentionally rejects plain-HTTP server URLs.

## Run locally

From `mobile/`:

```powershell
npm start
```

Press `a` in the Expo terminal to open an Android emulator, or scan the QR code with a compatible Expo development app. Set the server address to the externally trusted HTTPS URL that points to the host; a private HTTP LAN address will not work. The server must have the mobile authentication routes enabled and a mobile account created by an administrator.

For Android builds, use the standard Expo/EAS workflow after configuring the app's Android application ID and signing credentials for your organization. Never commit signing keys or credentials.

## Security behavior

- Login uses an individual mobile account with the admin, operator, or reviewer role.
- The API base address must be HTTPS; the app will not allow an HTTP override.
- The bearer token is stored with `expo-secure-store` and removed when the server reports an expired or revoked session.
- People and attendance lists are read-only and paginated. Face images, face embeddings, consent values, and recognition confidence are not displayed.
- Logging out clears the local token immediately and then asks the host to revoke it. If the host is unreachable, the token expires automatically after eight hours.

## Current screens

- **Overview:** today's student attendance metrics and class summaries.
- **People:** searchable, role-filtered directory with class membership.
- **Attendance:** newest-first attendance activity.

The mobile API's filtering, access-control, and response contract are documented in the root [README](../README.md).
