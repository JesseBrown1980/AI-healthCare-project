import React, { useEffect, useState } from 'react';
import { View, Text, ActivityIndicator, StyleSheet, ScrollView, Button, Alert } from 'react-native';

const PatientDetailScreen = ({ route, client }) => {
  const { patient } = route.params;
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await client.analyzePatient(patient.id);
      setAnalysis(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalysis();
  }, []);

  const renderSection = (title, content) => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <Text style={styles.body}>{content || 'No data provided.'}</Text>
    </View>
  );

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 32 }}>
      <Text style={styles.header}>{patient.name || patient.full_name || 'Patient'}</Text>
      <Text style={styles.meta}>ID: {patient.id}</Text>
      <Text style={styles.meta}>MRN: {patient.mrn || 'N/A'}</Text>
      <Button title="Refresh analysis" onPress={loadAnalysis} />
      {loading && <ActivityIndicator style={{ marginTop: 16 }} />}
      {error && (
        <Text style={styles.error} onPress={() => Alert.alert('Error', error)}>
          {error}
        </Text>
      )}
      {analysis && (
        <View>
          {renderSection('Summary', analysis.summary)}
          {renderSection('Alerts', analysis.alerts || analysis.alerts_summary)}
          {renderSection('Risk Score', analysis.risk_score?.toString() || analysis.risk)}
          {renderSection('Recommendations', analysis.recommendations)}
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#fff',
  },
  header: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  meta: {
    color: '#555',
    marginBottom: 4,
  },
  section: {
    marginTop: 16,
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#F4F7FB',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 6,
  },
  body: {
    fontSize: 14,
    lineHeight: 20,
  },
  error: {
    marginTop: 12,
    color: '#c1121f',
  },
});

export default PatientDetailScreen;
