# Face Attendance mobile app

The Expo app is a read-only Android/iOS companion for the existing attendance host. The server remains the source of truth; the app does not enroll faces, recognize faces, edit people, or change attendance.

## Requirements

- Node.js and npm.
- The project dependencies installed with `npm install` from this directory.
- An Expo-compatible Android device/emulator or iOS device/simulator.
- A trusted HTTPS certificate for the attendance host. The mobile app intentionally rejects plain-HTTP server URLs.

## Run locally

From `mobile/`:

```powershell
npm start
```

Press `a` in the Expo terminal to open an Android emulator, or scan the QR code with a compatible Expo development app. Install a development or production build: native Bonjour discovery is unavailable in Expo Go. On the login screen, the app searches the current Wi-Fi network and fills in a discovered HTTPS attendance host after validating its certificate and health endpoint. Local-network permission must be allowed. You can still enter a trusted HTTPS address manually. The server must have a mobile account created by an administrator.

## Secure local Wi-Fi discovery

The host advertises `_faceattendance._tcp.local` only when launched with TLS configured. Use a school-managed CA to issue a server certificate whose DNS Subject Alternative Name is the host's discovery name, such as `attendance-host.local`. The devices must trust that CA. The host name must also resolve through mDNS on the target network; test this on the oldest supported Android and iOS devices before deployment.

Configure the server environment before running the root `run.bat` or `run.sh` launcher:

```powershell
$env:MOBILE_TLS_CERT_FILE = "C:\school-certs\attendance-host.crt"
$env:MOBILE_TLS_KEY_FILE = "C:\school-certs\attendance-host.key"
$env:MOBILE_DISCOVERY_HOSTNAME = "attendance-host"
$env:MOBILE_HTTPS_PORT = "8443"
.\run.bat
```

`MOBILE_DISCOVERY_HOSTNAME` is the certificate hostname without `.local`; the service advertises `attendance-host.local`. Keep the private key outside source control and restrict its file permissions. The host listens for HTTPS on the configured port (8443 by default), and advertises its service only after the HTTPS server starts. Without both certificate and key settings, the existing HTTP kiosk/admin server remains on port 8000 and the app does not discover it.

For Android, package the CA certificate into a native build by setting `MOBILE_TRUSTED_CA_FILE` to the CA's public PEM certificate file while generating the app's native project/build. The Expo config plugin adds it as an additional trust anchor for `.local` hosts; system CA trust remains enabled and cleartext traffic remains disabled. For iOS, install and trust the school's CA on each device, or distribute it with the school's managed device profile. Rebuild and reinstall the native app after changing its trust configuration. Never package the server private key in the mobile app.

The mDNS record only helps locate a server; it does not authenticate it. The app accepts only HTTPS, validates the platform's certificate trust and the health API response, and never sends the username or password during discovery. If local-network discovery or certificate validation fails, use the manual HTTPS field; do not switch to HTTP.

For Android builds, use the standard Expo/EAS workflow after configuring the app's Android application ID and signing credentials for your organization. Never commit signing keys or credentials.

## Security behavior

- Login uses an individual mobile account with the admin, operator, or reviewer role.
- The API base address must be HTTPS; the app will not allow an HTTP override.
- Local discovery is automatic on native builds and uses mDNS; a discovered server is selected only after normal HTTPS certificate validation succeeds.
- The bearer token is stored with `expo-secure-store` and removed when the server reports an expired or revoked session.
- People and attendance lists are read-only and paginated. Face images, face embeddings, consent values, and recognition confidence are not displayed.
- Logging out clears the local token immediately and then asks the host to revoke it. If the host is unreachable, the token expires automatically after eight hours.

## Current screens

- **Overview:** today's student attendance metrics and class summaries.
- **People:** searchable, role-filtered directory with class membership.
- **Attendance:** newest-first attendance activity.

The mobile API's filtering, access-control, and response contract are documented in the root [README](../README.md).
