import { useEffect, useState } from 'react';
import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';
import { Platform } from 'react-native';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export const usePushNotifications = (client) => {
  const [pushToken, setPushToken] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const register = async () => {
      try {
        if (!Constants.isDevice) {
          setError('Push notifications require a physical device.');
          return;
        }

        const { status: existingStatus } = await Notifications.getPermissionsAsync();
        let finalStatus = existingStatus;
        if (existingStatus !== 'granted') {
          const { status } = await Notifications.requestPermissionsAsync();
          finalStatus = status;
        }

        if (finalStatus !== 'granted') {
          setError('Permission not granted for push notifications.');
          return;
        }

        const token = (await Notifications.getExpoPushTokenAsync()).data;
        setPushToken(token);

        if (client && token) {
          client.registerPushToken(token).catch((e) => setError(e.message));
        }

        if (Platform.OS === 'android') {
          await Notifications.setNotificationChannelAsync('default', {
            name: 'default',
            importance: Notifications.AndroidImportance.MAX,
            vibrationPattern: [0, 250, 250, 250],
            lightColor: '#0D6EFD',
          });
        }
      } catch (e) {
        setError(e.message);
      }
    };

    register();
  }, [client]);

  return { pushToken, error };
};
