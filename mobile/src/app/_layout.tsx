import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { Text, View } from 'react-native';
import { AuthProvider, useAuth } from '../auth/AuthProvider';
import { colors, Loading } from '../components/ui';

function Navigation() {
  const { bootstrapping, user } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (bootstrapping) return;
    const inApp = segments[0] === '(tabs)';
    if (user && !inApp) router.replace('/(tabs)');
    if (!user && inApp) router.replace('/login');
  }, [bootstrapping, router, segments, user]);

  if (bootstrapping) {
    return (
      <View style={{ backgroundColor: colors.background, flex: 1 }}>
        <Loading label="Checking your secure session…" />
      </View>
    );
  }

  return (
    <>
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}>
        <Stack.Screen name="login" />
        <Stack.Screen name="(tabs)" />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <Navigation />
    </AuthProvider>
  );
}
