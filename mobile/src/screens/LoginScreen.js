import React, { useState } from 'react';
import { View, Text, TextInput, Button, StyleSheet, Alert } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import Constants from 'expo-constants';
import { ApiClient } from '../api/client';

const LoginScreen = ({ onAuthenticated }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState('');
  const [baseUrl, setBaseUrl] = useState(Constants.expoConfig?.extra?.apiBaseUrl || '');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    try {
      const client = new ApiClient(null, baseUrl);
      const result = await client.login({ email, password });
      if (result?.token) {
        await SecureStore.setItemAsync('apiToken', result.token);
        await SecureStore.setItemAsync('apiBaseUrl', baseUrl);
        onAuthenticated(result.token, baseUrl);
      } else {
        Alert.alert('Login failed', 'Server did not return a token.');
      }
    } catch (error) {
      Alert.alert('Login failed', error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleToken = async () => {
    if (!token) {
      Alert.alert('Missing token', 'Enter a token first.');
      return;
    }
    await SecureStore.setItemAsync('apiToken', token);
    await SecureStore.setItemAsync('apiBaseUrl', baseUrl);
    onAuthenticated(token, baseUrl);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Clinician Alerts</Text>
      <TextInput
        placeholder="API base URL"
        value={baseUrl}
        onChangeText={setBaseUrl}
        style={styles.input}
        autoCapitalize="none"
      />
      <Text style={styles.section}>Login with credentials</Text>
      <TextInput
        placeholder="Email"
        value={email}
        onChangeText={setEmail}
        style={styles.input}
        autoCapitalize="none"
      />
      <TextInput
        placeholder="Password"
        value={password}
        onChangeText={setPassword}
        style={styles.input}
        secureTextEntry
      />
      <Button title={loading ? 'Signing in...' : 'Sign in'} onPress={handleLogin} disabled={loading} />

      <Text style={styles.section}>Or use an API token</Text>
      <TextInput
        placeholder="API token"
        value={token}
        onChangeText={setToken}
        style={styles.input}
        autoCapitalize="none"
      />
      <Button title="Continue with token" onPress={handleToken} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    backgroundColor: '#fff',
    justifyContent: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#0D6EFD',
  },
  section: {
    marginTop: 16,
    marginBottom: 8,
    fontWeight: 'bold',
  },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
});

export default LoginScreen;
