import Zeroconf, { Service } from 'react-native-zeroconf';
import { ApiError, fetchJson, normalizeApiBaseUrl } from './api';

type MobileHealth = {
  status: string;
  api_version: string;
  server_name: string;
};

const SERVICE_TYPE = 'faceattendance';

export function discoverAttendanceHost(
  onDiscovered: (serverUrl: string) => void,
  onStatus: (message: string) => void,
): () => void {
  const zeroconf = new Zeroconf();
  let active = true;
  const checkedHosts = new Set<string>();

  const onResolved = (service: Service) => {
    if (service.txt.scheme !== 'https' || service.txt.api !== '1') return;

    const hostname = service.txt.hostname?.replace(/\.$/, '').toLowerCase();
    if (
      !hostname ||
      !hostname.endsWith('.local') ||
      !hostname
        .split('.')
        .every((label) => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label))
    ) {
      return;
    }
    if (!Number.isInteger(service.port) || service.port < 1 || service.port > 65535) {
      return;
    }

    let serverUrl: string;
    try {
      serverUrl = normalizeApiBaseUrl(`https://${hostname}:${service.port}`);
    } catch (error) {
      if (error instanceof ApiError) return;
      throw error;
    }
    if (checkedHosts.has(serverUrl)) return;
    checkedHosts.add(serverUrl);

    void fetchJson<MobileHealth>(serverUrl, '/api/v1/mobile/health')
      .then((health) => {
        if (
          !active ||
          health.status !== 'ok' ||
          health.api_version !== '1' ||
          health.server_name !== 'Face Attendance Host'
        ) {
          return;
        }
        onDiscovered(serverUrl);
        onStatus(`Attendance host found: ${hostname}`);
      })
      .catch(() => {
        if (active) {
          onStatus(
            'A host was found, but its HTTPS certificate could not be verified. Check the school certificate setup.',
          );
        }
      });
  };

  const onError = () => {
    if (active) {
      onStatus('Could not scan this Wi-Fi network. Check local-network permission.');
    }
  };

  zeroconf.on('resolved', onResolved);
  zeroconf.on('error', onError);
  onStatus('Checking local-network permission…');

  void zeroconf
    .checkLocalNetworkAccess({ timeout: 5 })
    .then((access) => {
      if (!active) return;
      if (access !== 'granted') {
        onStatus('Allow local-network access to discover the attendance host.');
        return;
      }
      onStatus('Searching for an attendance host on this Wi-Fi…');
      zeroconf.scan({ type: SERVICE_TYPE, protocol: 'tcp', domain: 'local.' });
    })
    .catch(() => {
      if (active) {
        onStatus('Could not request local-network access. Enter the HTTPS address manually.');
      }
    });

  return () => {
    active = false;
    zeroconf.stop();
    zeroconf.removeAllListeners();
    zeroconf.removeDeviceListeners();
  };
}
