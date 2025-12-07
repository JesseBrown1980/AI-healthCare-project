import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, FlatList, TouchableOpacity, RefreshControl, StyleSheet } from 'react-native';

const PatientListScreen = ({ client, navigation }) => {
  const [patients, setPatients] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [patientResponse, alertResponse] = await Promise.all([
        client.fetchPatients(),
        client.fetchAlerts(),
      ]);
      setPatients(patientResponse?.patients || patientResponse || []);
      setAlerts(alertResponse?.alerts || alertResponse || []);
    } catch (error) {
      console.error('Failed to load patients', error);
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const renderPatient = ({ item }) => (
    <TouchableOpacity
      style={styles.card}
      onPress={() => navigation.navigate('PatientDetail', { patient: item })}
    >
      <Text style={styles.cardTitle}>{item.name || item.full_name || 'Patient'}</Text>
      <Text>ID: {item.id}</Text>
      <Text>Age: {item.age || 'N/A'}</Text>
      <Text>MRN: {item.mrn || 'N/A'}</Text>
    </TouchableOpacity>
  );

  const renderAlert = ({ item }) => (
    <View style={styles.alertCard}>
      <Text style={styles.cardTitle}>{item.title || item.type}</Text>
      <Text style={styles.alertDetail}>{item.summary || item.description}</Text>
      <Text style={styles.alertMeta}>{new Date(item.timestamp || item.created_at).toLocaleString()}</Text>
    </View>
  );

  return (
    <FlatList
      ListHeaderComponent={
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Assigned Patients</Text>
        </View>
      }
      data={patients}
      keyExtractor={(item, index) => `${item.id || index}`}
      renderItem={renderPatient}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={loadData} />}
      ListFooterComponent={
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Recent Alerts</Text>
          <FlatList
            data={alerts}
            keyExtractor={(item, index) => `${item.id || index}`}
            renderItem={renderAlert}
            ListEmptyComponent={<Text>No alerts yet.</Text>}
          />
        </View>
      }
      ListEmptyComponent={<Text style={styles.empty}>No patients assigned.</Text>}
      contentContainerStyle={styles.container}
    />
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 16,
  },
  section: {
    marginVertical: 12,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  card: {
    backgroundColor: '#fff',
    padding: 16,
    marginBottom: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#e5e5e5',
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 4,
    elevation: 2,
  },
  alertCard: {
    backgroundColor: '#FFF4E5',
    padding: 12,
    marginBottom: 10,
    borderRadius: 8,
    borderColor: '#F1C232',
    borderWidth: 1,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  alertDetail: {
    marginBottom: 4,
  },
  alertMeta: {
    fontSize: 12,
    color: '#555',
  },
  empty: {
    textAlign: 'center',
    marginTop: 32,
  },
});

export default PatientListScreen;
