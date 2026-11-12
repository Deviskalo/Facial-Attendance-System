import { PropsWithChildren, ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  ViewStyle,
} from 'react-native';

export const colors = {
  background: '#0b1115',
  surface: '#121c22',
  surfaceRaised: '#18252c',
  border: '#28383f',
  text: '#eef7f7',
  muted: '#9aaeb3',
  accent: '#55d6be',
  danger: '#ff8b82',
  warning: '#f6c56a',
  white: '#ffffff',
};

export function Page({ children }: PropsWithChildren) {
  return <View style={styles.page}>{children}</View>;
}

export function Heading({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <View style={styles.heading}>
      <Text style={styles.eyebrow}>{eyebrow}</Text>
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}

export function Panel({
  children,
  style,
}: PropsWithChildren<{ style?: ViewStyle }>) {
  return <View style={[styles.panel, style]}>{children}</View>;
}

export function Notice({
  message,
  tone = 'error',
}: {
  message: string;
  tone?: 'error' | 'info';
}) {
  return (
    <View
      accessibilityRole="alert"
      style={[
        styles.notice,
        tone === 'error' ? styles.noticeError : styles.noticeInfo,
      ]}
    >
      <Text
        style={[
          styles.noticeText,
          tone === 'error' ? styles.noticeErrorText : styles.noticeInfoText,
        ]}
      >
        {message}
      </Text>
    </View>
  );
}

export function Field({
  label,
  ...props
}: React.ComponentProps<typeof TextInput> & { label: string }) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        placeholderTextColor={colors.muted}
        style={styles.input}
        {...props}
      />
    </View>
  );
}

export function ActionButton({
  title,
  onPress,
  disabled,
  variant = 'primary',
  trailing,
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary';
  trailing?: ReactNode;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        variant === 'secondary' && styles.buttonSecondary,
        disabled && styles.buttonDisabled,
        pressed && !disabled && styles.buttonPressed,
      ]}
    >
      {trailing}
      <Text
        style={[
          styles.buttonText,
          variant === 'secondary' && styles.buttonTextSecondary,
        ]}
      >
        {title}
      </Text>
    </Pressable>
  );
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <View style={styles.loading}>
      <ActivityIndicator color={colors.accent} />
      <Text style={styles.loadingText}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.background, padding: 20 },
  heading: { gap: 7, marginBottom: 22 },
  eyebrow: {
    color: colors.accent,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1.7,
  },
  title: { color: colors.text, fontSize: 29, fontWeight: '800' },
  subtitle: { color: colors.muted, fontSize: 14, lineHeight: 21 },
  panel: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 18,
    borderWidth: 1,
    padding: 17,
  },
  notice: { borderRadius: 12, borderWidth: 1, marginBottom: 16, padding: 12 },
  noticeError: { backgroundColor: '#321e21', borderColor: '#704046' },
  noticeInfo: { backgroundColor: '#182a30', borderColor: '#34565e' },
  noticeText: { fontSize: 13, lineHeight: 19 },
  noticeErrorText: { color: '#ffc1bb' },
  noticeInfoText: { color: '#b8e4e6' },
  field: { gap: 8, marginBottom: 16 },
  fieldLabel: { color: colors.text, fontSize: 13, fontWeight: '700' },
  input: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.border,
    borderRadius: 12,
    borderWidth: 1,
    color: colors.text,
    fontSize: 16,
    minHeight: 50,
    paddingHorizontal: 14,
  },
  button: {
    alignItems: 'center',
    backgroundColor: colors.accent,
    borderRadius: 12,
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'center',
    minHeight: 50,
    paddingHorizontal: 16,
  },
  buttonSecondary: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.border,
    borderWidth: 1,
  },
  buttonDisabled: { opacity: 0.55 },
  buttonPressed: { opacity: 0.8 },
  buttonText: { color: '#06221e', fontSize: 15, fontWeight: '800' },
  buttonTextSecondary: { color: colors.text },
  loading: {
    alignItems: 'center',
    flex: 1,
    gap: 12,
    justifyContent: 'center',
  },
  loadingText: { color: colors.muted, fontSize: 14 },
});
