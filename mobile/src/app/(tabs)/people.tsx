import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useAuth } from '../../auth/AuthProvider';
import { ApiError, Page, Person } from '../../lib/api';
import { ActionButton, colors, Field, Heading, Loading, Notice, Panel } from '../../components/ui';

const PAGE_SIZE = 50;
const ROLES = ['All', 'STUDENT', 'TEACHER', 'STAFF', 'EMPLOYEE'] as const;
type RoleFilter = (typeof ROLES)[number];

export default function PeopleScreen() {
  const { request } = useAuth();
  const [people, setPeople] = useState<Person[]>([]);
  const [role, setRole] = useState<RoleFilter>('All');
  const [searchText, setSearchText] = useState('');
  const [search, setSearch] = useState('');
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
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(nextOffset) });
    if (role !== 'All') params.set('role', role);
    if (search) params.set('search', search);
    try {
      const page = await request<Page<Person>>(`/api/v1/mobile/people?${params.toString()}`);
      setPeople((current) => nextOffset === 0 ? page.items : [...current, ...page.items]);
      setTotal(page.total);
      setOffset(nextOffset);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Could not load people.');
    } finally {
      setLoading(false);
      setRefreshing(false);
      setLoadingMore(false);
    }
  }, [request, role, search]);

  useEffect(() => {
    void load(0);
  }, [load]);

  const applySearch = () => {
    setSearch(searchText.trim());
  };

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => void load(0, true)} tintColor={colors.accent} />
      }
    >
      <Heading eyebrow="DIRECTORY" title="People" subtitle={`${total} active records`} />
      <Field
        label="Search people"
        value={searchText}
        onChangeText={setSearchText}
        placeholder="Name, ID, or department"
        returnKeyType="search"
        onSubmitEditing={applySearch}
      />
      <ActionButton title="Search" onPress={applySearch} />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filters}>
        {ROLES.map((item) => (
          <Pressable
            key={item}
            onPress={() => setRole(item)}
            style={[styles.filter, role === item && styles.filterActive]}
          >
            <Text style={[styles.filterText, role === item && styles.filterTextActive]}>
              {item === 'All' ? 'Everyone' : item[0] + item.slice(1).toLowerCase()}
            </Text>
          </Pressable>
        ))}
      </ScrollView>
      {error ? <Notice message={error} /> : null}
      {loading && !people.length ? <Loading label="Loading directory…" /> : null}
      {!loading && people.length === 0 ? (
        <Panel><Text style={styles.empty}>No matching people found.</Text></Panel>
      ) : null}
      {people.map((person) => (
        <Panel key={person.id} style={styles.personCard}>
          <View style={styles.personTop}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{person.name.trim().slice(0, 1).toUpperCase()}</Text>
            </View>
            <View style={styles.personIdentity}>
              <Text style={styles.name}>{person.name}</Text>
              <Text style={styles.secondary}>{person.id} · {person.department}</Text>
            </View>
            <Text style={styles.role}>{person.role.toLowerCase()}</Text>
          </View>
          {person.classes.length ? (
            <Text style={styles.classes}>{person.classes.map((item) => item.name).join(' · ')}</Text>
          ) : null}
        </Panel>
      ))}
      {people.length < total ? (
        <ActionButton
          title={loadingMore ? 'Loading…' : 'Load more'}
          onPress={() => void load(offset + PAGE_SIZE)}
          disabled={loadingMore}
          variant="secondary"
          trailing={loadingMore ? <ActivityIndicator color={colors.accent} /> : undefined}
        />
      ) : null}
      <Text style={styles.readOnly}>Personal and biometric details are intentionally excluded from this directory.</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { backgroundColor: colors.background, flex: 1 },
  content: { gap: 12, padding: 20, paddingBottom: 30 },
  filters: { gap: 8, paddingVertical: 2 },
  filter: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 20, borderWidth: 1, paddingHorizontal: 14, paddingVertical: 9 },
  filterActive: { backgroundColor: '#153b37', borderColor: colors.accent },
  filterText: { color: colors.muted, fontSize: 12, fontWeight: '700' },
  filterTextActive: { color: colors.accent },
  personCard: { gap: 10 },
  personTop: { alignItems: 'center', flexDirection: 'row', gap: 11 },
  avatar: { alignItems: 'center', backgroundColor: '#193b3a', borderRadius: 22, height: 42, justifyContent: 'center', width: 42 },
  avatarText: { color: colors.accent, fontSize: 16, fontWeight: '800' },
  personIdentity: { flex: 1, gap: 4 },
  name: { color: colors.text, fontSize: 14, fontWeight: '700' },
  secondary: { color: colors.muted, fontSize: 11 },
  role: { color: colors.accent, fontSize: 10, fontWeight: '800', textTransform: 'uppercase' },
  classes: { borderTopColor: colors.border, borderTopWidth: 1, color: colors.muted, fontSize: 11, paddingTop: 10 },
  empty: { color: colors.muted, paddingVertical: 6 },
  readOnly: { color: '#71858a', fontSize: 11, lineHeight: 17, textAlign: 'center' },
});
