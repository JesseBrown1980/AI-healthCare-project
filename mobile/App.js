import React, { useEffect, useMemo, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { View, ActivityIndicator, Alert } from 'react-native';
import * as SecureStore from 'expo-secure-store';

import LoginScreen from './src/screens/LoginScreen';
import PatientListScreen from './src/screens/PatientListScreen';
import PatientDetailScreen from './src/screens/PatientDetailScreen';
import { ApiClient } from './src/api/client';
import { usePushNotifications } from './src/hooks/usePushNotifications';

const Stack = createNativeStackNavigator();

export default function App() {
  const [token, setToken] = useState(null);
  const [baseUrl, setBaseUrl] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadCredentials = async () => {
      const storedToken = await SecureStore.getItemAsync('apiToken');
      const storedBaseUrl = await SecureStore.getItemAsync('apiBaseUrl');
      if (storedToken) {
        setToken(storedToken);
      }
      if (storedBaseUrl) {
        setBaseUrl(storedBaseUrl);
      }
      setLoading(false);
    };

    loadCredentials();
  }, []);

  const client = useMemo(() => (token ? new ApiClient(token, baseUrl) : null), [token, baseUrl]);

  const { error: pushError } = usePushNotifications(client);

  useEffect(() => {
    if (pushError) {
      Alert.alert('Push notification error', pushError);
    }
  }, [pushError]);

  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator />
      </View>
    );
  }

  if (!token) {
    return <LoginScreen onAuthenticated={(newToken, url) => { setToken(newToken); setBaseUrl(url); }} />;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Patients" options={{ title: 'Clinician Alerts' }}>
          {(props) => <PatientListScreen {...props} client={client} />}
        </Stack.Screen>
        <Stack.Screen
          name="PatientDetail"
          options={({ route }) => ({ title: route.params?.patient?.name || 'Patient' })}
        >
          {(props) => <PatientDetailScreen {...props} client={client} />}
        </Stack.Screen>
      </Stack.Navigator>
    </NavigationContainer>
  );
}
