import { useCallback, useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../../auth/AuthProvider';
import { ApiError, DashboardData } from '../../lib/api';
import { ActionButton, colors, Heading, Loading, Notice, Panel, Page } from '../../components/ui';

function Metric({
  label,
  value,
  detail,
  accent,
}: {
  label: string;
  value: number;
  detail: string;
  accent?: string;
}) {
  return (
    <Panel style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, accent ? { color: accent } : null]}>{value}</Text>
      <Text style={styles.metricDetail}>{detail}</Text>
    </Panel>
  );
}

export default function DashboardScreen() {
  const { request, user, signOut, startupError } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(startupError);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      setData(await request<DashboardData>('/api/v1/mobile/dashboard'));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Could not load the dashboard.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [request]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !data) return <Page><Loading label="Loading attendance overview…" /></Page>;

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => void load(true)}
          tintColor={colors.accent}
        />
      }
    >
      <View style={styles.topline}>
        <View style={styles.welcome}>
          <Text style={styles.welcomeLabel}>SIGNED IN AS {user?.role.toUpperCase()}</Text>
          <Text style={styles.welcomeName}>{user?.display_name}</Text>
        </View>
        <ActionButton title="Sign out" variant="secondary" onPress={() => void signOut()} />
      </View>
      <Heading
        eyebrow="TODAY AT A GLANCE"
        title="Attendance"
        subtitle={data ? new Date(`${data.date}T12:00:00`).toLocaleDateString(undefined, {
          weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
        }) : 'Your school overview'}
      />
      {error ? <Notice message={error} /> : null}
      {data ? (
        <>
          <View style={styles.metrics}>
            <Metric label="PRESENT" value={data.metrics.present} detail={`of ${data.metrics.enrolled} students`} accent={colors.accent} />
            <Metric label="LATE" value={data.metrics.late} detail="arrived after start" accent={colors.warning} />
            <Metric label="ABSENT" value={data.metrics.absent} detail="not checked in" accent={colors.danger} />
            <Metric label="ENROLLED" value={data.metrics.enrolled} detail="active students" />
          </View>
          <View style={styles.sectionHeading}>
            <Text style={styles.sectionTitle}>Class attendance</Text>
            <Text style={styles.sectionCount}>{data.classes.length} classes</Text>
          </View>
          {data.classes.length ? data.classes.map((item) => (
            <Panel key={item.class_name} style={styles.classCard}>
              <View style={styles.classTop}>
                <Text style={styles.className}>{item.class_name}</Text>
                <Text style={styles.classPercent}>
                  {item.enrolled ? Math.round((item.present / item.enrolled) * 100) : 0}%
                </Text>
              </View>
              <View style={styles.barTrack}>
                <View
                  style={[
                    styles.barFill,
                    { width: `${item.enrolled ? Math.min((item.present / item.enrolled) * 100, 100) : 0}%` },
                  ]}
                />
              </View>
              <Text style={styles.classMeta}>
                {item.present} present · {item.late} late · {item.absent} absent · {item.enrolled} enrolled
              </Text>
            </Panel>
          )) : (
            <Panel><Text style={styles.empty}>No class attendance data is available yet.</Text></Panel>
          )}
        </>
      ) : (
        <Panel>
          <Text style={styles.empty}>Dashboard data is not available.</Text>
          <ActionButton title="Try again" onPress={() => void load()} />
        </Panel>
      )}
      <Text style={styles.readOnly}>Mobile dashboard is read-only. Changes remain managed from the host application.</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { backgroundColor: colors.background, flex: 1 },
  content: { gap: 14, padding: 20, paddingBottom: 30 },
  topline: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  welcome: { flex: 1, gap: 4 },
  welcomeLabel: { color: colors.muted, fontSize: 9, fontWeight: '800', letterSpacing: 1 },
  welcomeName: { color: colors.text, fontSize: 15, fontWeight: '700' },
  metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  metric: { flexBasis: '47%', flexGrow: 1, gap: 7, minHeight: 116 },
  metricLabel: { color: colors.muted, fontSize: 10, fontWeight: '800', letterSpacing: 1 },
  metricValue: { color: colors.text, fontSize: 31, fontWeight: '800' },
  metricDetail: { color: colors.muted, fontSize: 11 },
  sectionHeading: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  sectionTitle: { color: colors.text, fontSize: 18, fontWeight: '800' },
  sectionCount: { color: colors.muted, fontSize: 12 },
  classCard: { gap: 12 },
  classTop: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  className: { color: colors.text, fontSize: 15, fontWeight: '700' },
  classPercent: { color: colors.accent, fontSize: 15, fontWeight: '800' },
  barTrack: { backgroundColor: colors.surfaceRaised, borderRadius: 99, height: 7, overflow: 'hidden' },
  barFill: { backgroundColor: colors.accent, borderRadius: 99, height: '100%' },
  classMeta: { color: colors.muted, fontSize: 11 },
  empty: { color: colors.muted, lineHeight: 20, marginBottom: 12 },
  readOnly: { color: '#71858a', fontSize: 11, lineHeight: 17, paddingTop: 7, textAlign: 'center' },
});
