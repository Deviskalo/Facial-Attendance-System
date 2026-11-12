import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../auth/AuthProvider';
import { ActionButton, colors, Field, Heading, Notice, Panel } from '../components/ui';

export default function LoginScreen() {
  const { signIn, serverUrl, startupError } = useAuth();
  const [server, setServer] = useState(serverUrl);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await signIn(server, username.trim(), password);
      setPassword('');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not sign in.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.keyboard}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.brand}>
          <View style={styles.brandMark}><Text style={styles.brandMarkText}>FA</Text></View>
          <Text style={styles.brandName}>FIELD ATTENDANCE</Text>
        </View>
        <Heading
          eyebrow="SCHOOL MANAGEMENT"
          title="Welcome back"
          subtitle="Sign in with the mobile account created by your attendance administrator."
        />
        {startupError ? <Notice message={startupError} /> : null}
        {error ? <Notice message={error} /> : null}
        <Panel>
          <Field
            autoCapitalize="none"
            autoCorrect={false}
            label="Secure server address"
            onChangeText={setServer}
            placeholder="https://attendance.yourschool.edu"
            value={server}
            keyboardType="url"
          />
          <Field
            autoCapitalize="none"
            autoCorrect={false}
            label="Username"
            onChangeText={setUsername}
            placeholder="Your individual account"
            value={username}
            textContentType="username"
          />
          <Field
            label="Password"
            onChangeText={setPassword}
            placeholder="Your password"
            value={password}
            secureTextEntry
            textContentType="password"
            onSubmitEditing={() => void submit()}
            returnKeyType="go"
          />
          <ActionButton
            title={submitting ? 'Signing in…' : 'Sign in securely'}
            onPress={() => void submit()}
            disabled={submitting || !server.trim() || !username.trim() || !password}
          />
        </Panel>
        <Text style={styles.security}>
          Your password is sent only to your configured HTTPS server. The access token is stored in this device’s secure storage.
        </Text>
        <Text style={styles.footer}>Read-only mobile access · Face Attendance Host</Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  keyboard: { backgroundColor: colors.background, flex: 1 },
  content: { flexGrow: 1, justifyContent: 'center', padding: 24 },
  brand: { alignItems: 'center', flexDirection: 'row', gap: 10, marginBottom: 34 },
  brandMark: {
    alignItems: 'center',
    backgroundColor: colors.accent,
    borderRadius: 12,
    height: 38,
    justifyContent: 'center',
    width: 38,
  },
  brandMarkText: { color: '#06221e', fontSize: 13, fontWeight: '900' },
  brandName: { color: colors.muted, fontSize: 11, fontWeight: '800', letterSpacing: 1.5 },
  security: { color: colors.muted, fontSize: 12, lineHeight: 18, marginTop: 16 },
  footer: { color: '#62787e', fontSize: 11, marginTop: 30, textAlign: 'center' },
});
