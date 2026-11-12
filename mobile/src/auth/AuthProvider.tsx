import * as SecureStore from 'expo-secure-store';
import {
  createContext,
  PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { Platform } from 'react-native';
import { ApiError, fetchJson, MobileUser, normalizeApiBaseUrl } from '../lib/api';

const TOKEN_KEY = 'mobile_access_token';
const SERVER_KEY = 'mobile_server_url';

type AuthContextValue = {
  bootstrapping: boolean;
  user: MobileUser | null;
  serverUrl: string;
  startupError: string | null;
  signIn: (serverUrl: string, username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  request: <T>(path: string) => Promise<T>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function assertNativeSecureStorage(): void {
  if (Platform.OS === 'web') {
    throw new ApiError('Sign-in is available in the Android and iOS app only.');
  }
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [bootstrapping, setBootstrapping] = useState(true);
  const [user, setUser] = useState<MobileUser | null>(null);
  const [serverUrl, setServerUrl] = useState('');
  const [token, setToken] = useState<string | null>(null);
  const [startupError, setStartupError] = useState<string | null>(null);

  const clearLocalSession = useCallback(async () => {
    setToken(null);
    setUser(null);
    try {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
    } catch {
      setStartupError('Could not remove the saved token from secure device storage.');
    }
  }, []);

  useEffect(() => {
    let active = true;
    const restoreSession = async () => {
      try {
        assertNativeSecureStorage();
        const [savedServerUrl, savedToken] = await Promise.all([
          SecureStore.getItemAsync(SERVER_KEY),
          SecureStore.getItemAsync(TOKEN_KEY),
        ]);
        if (!active) return;
        const normalizedUrl = savedServerUrl
          ? normalizeApiBaseUrl(savedServerUrl)
          : '';
        setServerUrl(normalizedUrl);
        if (savedToken && normalizedUrl) {
          setToken(savedToken);
          const currentUser = await fetchJson<MobileUser>(
            normalizedUrl,
            '/api/v1/mobile/me',
            savedToken,
          );
          if (active) setUser(currentUser);
        }
      } catch (error) {
        if (!active) return;
        if (error instanceof ApiError && error.status === 401) {
          await SecureStore.deleteItemAsync(TOKEN_KEY);
        } else {
          setStartupError(
            error instanceof Error ? error.message : 'Could not restore the saved session.',
          );
        }
      } finally {
        if (active) setBootstrapping(false);
      }
    };
    void restoreSession();
    return () => {
      active = false;
    };
  }, []);

  const signIn = useCallback(
    async (rawServerUrl: string, username: string, password: string) => {
      assertNativeSecureStorage();
      const normalizedUrl = normalizeApiBaseUrl(rawServerUrl);
      const result = await fetchJson<{
        access_token: string;
        user: MobileUser;
      }>(normalizedUrl, '/api/v1/mobile/auth/login', undefined, {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });

      try {
        await SecureStore.setItemAsync(TOKEN_KEY, result.access_token);
        await SecureStore.setItemAsync(SERVER_KEY, normalizedUrl);
      } catch {
        try {
          await fetchJson(
            normalizedUrl,
            '/api/v1/mobile/auth/logout',
            result.access_token,
            { method: 'POST' },
          );
        } catch {
          // The local session is never established if the secure token write fails.
        }
        await Promise.all([
          SecureStore.deleteItemAsync(TOKEN_KEY).catch(() => undefined),
          SecureStore.deleteItemAsync(SERVER_KEY).catch(() => undefined),
        ]);
        throw new ApiError('Could not securely save the session on this device.');
      }

      setServerUrl(normalizedUrl);
      setToken(result.access_token);
      setUser(result.user);
      setStartupError(null);
    },
    [],
  );

  const signOut = useCallback(async () => {
    const currentToken = token;
    const currentServerUrl = serverUrl;
    setStartupError(null);
    await clearLocalSession();
    let signOutWarning: string | null = null;
    if (currentToken && currentServerUrl) {
      try {
        await fetchJson(
          currentServerUrl,
          '/api/v1/mobile/auth/logout',
          currentToken,
          { method: 'POST' },
        );
      } catch {
        signOutWarning =
          'Signed out on this device, but the server could not be reached to revoke the token. It will expire automatically.';
      }
    }
    if (signOutWarning) setStartupError(signOutWarning);
  }, [clearLocalSession, serverUrl, token]);

  const request = useCallback(
    async <T,>(path: string): Promise<T> => {
      if (!token || !serverUrl) {
        throw new ApiError('Sign in to continue.', 401);
      }
      try {
        return await fetchJson<T>(serverUrl, path, token);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          await clearLocalSession();
        }
        throw error;
      }
    },
    [clearLocalSession, serverUrl, token],
  );

  const value = useMemo(
    () => ({
      bootstrapping,
      user,
      serverUrl,
      startupError,
      signIn,
      signOut,
      request,
    }),
    [bootstrapping, user, serverUrl, startupError, signIn, signOut, request],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider.');
  }
  return context;
}
