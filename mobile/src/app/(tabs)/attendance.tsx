import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../../auth/AuthProvider';
import { ApiError, AttendanceRecord, Page } from '../../lib/api';
import { ActionButton, colors, Heading, Loading, Notice, Panel } from '../../components/ui';

const PAGE_SIZE = 50;

function formatTimestamp(value: string): string {
  const parsed = new Date(value.replace(' ', 'T'));
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
}

export default function AttendanceScreen() {
  const { request } = useAuth();
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const load = useCallback(async (nextOffset = 0, refresh = false) => {
    if (refresh) setRefreshing(true);
    else if (nextOffset === 0) setLoading(true);
    else setLoadingMore(true);
    setError(null);
    try {
      const page = await request<Page<AttendanceRecord>>(
        `/api/v1/mobile/attendance?limit=${PAGE_SIZE}&offset=${nextOffset}`,
      );
      setRecords((current) => nextOffset === 0 ? page.items : [...current, ...page.items]);
      setTotal(page.total);
      setOffset(nextOffset);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Could not load attendance.');
    } finally {
      setLoading(false);
      setRefreshing(false);
      setLoadingMore(false);
    }
  }, [request]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => void load(0, true)} tintColor={colors.accent} />
      }
    >
      <Heading eyebrow="ATTENDANCE LOG" title="Recent activity" subtitle={`${total} records · newest first`} />
      {error ? <Notice message={error} /> : null}
      {loading && !records.length ? <Loading label="Loading attendance…" /> : null}
      {!loading && records.length === 0 ? (
        <Panel><Text style={styles.empty}>No attendance records are available.</Text></Panel>
      ) : null}
      {records.map((record) => {
        const checkIn = record.event_type === 'CHECK_IN';
        return (
          <Panel key={record.id} style={styles.record}>
            <View style={styles.recordTop}>
              <View style={[styles.eventMark, checkIn ? styles.markIn : styles.markOut]}>
                <Text style={[styles.eventMarkText, checkIn ? styles.textIn : styles.textOut]}>
                  {checkIn ? 'IN' : 'OUT'}
                </Text>
              </View>
              <View style={styles.recordIdentity}>
                <Text style={styles.name}>{record.name}</Text>
                <Text style={styles.secondary}>{record.employee_id} · {record.role.toLowerCase()}</Text>
              </View>
              <Text style={[styles.status, record.status === 'LATE' && styles.late, record.status === 'MANUAL' && styles.manual]}>
                {record.status === 'LATE' ? 'Late' : record.status === 'MANUAL' ? 'Manual' : 'On time'}
              </Text>
            </View>
            <Text style={styles.time}>{formatTimestamp(record.timestamp)} · {record.department}</Text>
          </Panel>
        );
      })}
      {records.length < total ? (
        <ActionButton
          title={loadingMore ? 'Loading…' : 'Load more'}
          onPress={() => void load(offset + PAGE_SIZE)}
          disabled={loadingMore}
          variant="secondary"
          trailing={loadingMore ? <ActivityIndicator color={colors.accent} /> : undefined}
        />
      ) : null}
      <Text style={styles.readOnly}>Attendance records are view-only in the mobile app.</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { backgroundColor: colors.background, flex: 1 },
  content: { gap: 12, padding: 20, paddingBottom: 30 },
  record: { gap: 12 },
  recordTop: { alignItems: 'center', flexDirection: 'row', gap: 11 },
  eventMark: { alignItems: 'center', borderRadius: 9, height: 36, justifyContent: 'center', width: 40 },
  markIn: { backgroundColor: '#153b37' },
  markOut: { backgroundColor: '#263440' },
  eventMarkText: { fontSize: 10, fontWeight: '900' },
  textIn: { color: colors.accent },
  textOut: { color: '#b8c5e1' },
  recordIdentity: { flex: 1, gap: 4 },
  name: { color: colors.text, fontSize: 14, fontWeight: '700' },
  secondary: { color: colors.muted, fontSize: 11 },
  status: { color: colors.accent, fontSize: 11, fontWeight: '800' },
  late: { color: colors.warning },
  manual: { color: colors.muted },
  time: { borderTopColor: colors.border, borderTopWidth: 1, color: colors.muted, fontSize: 11, paddingTop: 10 },
  empty: { color: colors.muted, paddingVertical: 6 },
  readOnly: { color: '#71858a', fontSize: 11, lineHeight: 17, textAlign: 'center' },
});
