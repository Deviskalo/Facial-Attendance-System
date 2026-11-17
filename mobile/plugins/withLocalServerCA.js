const fs = require('node:fs');
const path = require('node:path');
const {
  withAndroidManifest,
  withDangerousMod,
} = require('@expo/config-plugins');

const NETWORK_SECURITY_CONFIG = 'attendance_network_security_config';
const CA_RESOURCE_NAME = 'attendance_local_ca';

function withLocalServerCA(config) {
  const configuredCA = process.env.MOBILE_TRUSTED_CA_FILE;
  if (!configuredCA) {
    return config;
  }

  config = withAndroidManifest(config, (modConfig) => {
    const application = modConfig.modResults.manifest.application?.[0];
    if (!application) {
      throw new Error('Android manifest is missing its application element.');
    }
    application.$['android:networkSecurityConfig'] =
      `@xml/${NETWORK_SECURITY_CONFIG}`;
    return modConfig;
  });

  return withDangerousMod(config, [
    'android',
    async (modConfig) => {
      const sourceCA = path.resolve(
        modConfig.modRequest.projectRoot,
        configuredCA,
      );
      if (!fs.existsSync(sourceCA) || !fs.statSync(sourceCA).isFile()) {
        throw new Error(
          `MOBILE_TRUSTED_CA_FILE does not point to a certificate file: ${sourceCA}`,
        );
      }

      const platformRoot = modConfig.modRequest.platformProjectRoot;
      const rawDirectory = path.join(platformRoot, 'app', 'src', 'main', 'res', 'raw');
      const xmlDirectory = path.join(platformRoot, 'app', 'src', 'main', 'res', 'xml');
      fs.mkdirSync(rawDirectory, { recursive: true });
      fs.mkdirSync(xmlDirectory, { recursive: true });
      fs.copyFileSync(sourceCA, path.join(rawDirectory, `${CA_RESOURCE_NAME}.crt`));
      fs.writeFileSync(
        path.join(xmlDirectory, `${NETWORK_SECURITY_CONFIG}.xml`),
        `<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
  <base-config cleartextTrafficPermitted="false">
    <trust-anchors>
      <certificates src="system" />
    </trust-anchors>
  </base-config>
  <domain-config cleartextTrafficPermitted="false">
    <domain includeSubdomains="true">local</domain>
    <trust-anchors>
      <certificates src="system" />
      <certificates src="@raw/${CA_RESOURCE_NAME}" />
    </trust-anchors>
  </domain-config>
</network-security-config>
`,
      );
      return modConfig;
    },
  ]);
}

module.exports = withLocalServerCA;
