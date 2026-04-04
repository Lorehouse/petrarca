import React, { useEffect, useRef, useState } from 'react';
import { Text, Animated, StyleSheet, Platform } from 'react-native';
import { colors, fonts } from '../design/tokens';
import { onVoiceUploadResult } from '../lib/voice-upload-service';

interface ToastMessage {
  text: string;
  success: boolean;
  key: number;
}

export default function VoiceUploadToast() {
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const slideAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    return onVoiceUploadResult((nodeTitle, success) => {
      setToast({
        text: success
          ? `Voice recall uploaded: ${nodeTitle}`
          : `Upload expired: ${nodeTitle}`,
        success,
        key: Date.now(),
      });
    });
  }, []);

  useEffect(() => {
    if (!toast) return;
    slideAnim.setValue(0);
    Animated.timing(slideAnim, {
      toValue: 1,
      duration: 250,
      useNativeDriver: true,
    }).start();

    const timer = setTimeout(() => {
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 200,
        useNativeDriver: true,
      }).start(() => setToast(null));
    }, 3000);

    return () => clearTimeout(timer);
  }, [toast?.key]);

  if (!toast) return null;

  return (
    <Animated.View
      style={[
        styles.toast,
        {
          opacity: slideAnim,
          transform: [{
            translateY: slideAnim.interpolate({
              inputRange: [0, 1],
              outputRange: [40, 0],
            }),
          }],
        },
      ]}
    >
      <Text style={styles.icon}>{toast.success ? '\u2713' : '\u2717'}</Text>
      <Text style={styles.text} numberOfLines={1}>{toast.text}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  toast: {
    position: 'absolute',
    bottom: 48,
    left: 16,
    right: 16,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.ink,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 4,
    zIndex: 300,
    gap: 6,
    ...(Platform.OS === 'web' ? {
      boxShadow: '0 -2px 12px rgba(0,0,0,0.15)',
    } : {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: -2 },
      shadowOpacity: 0.15,
      shadowRadius: 12,
      elevation: 6,
    }) as any,
  },
  icon: {
    fontFamily: fonts.ui,
    fontSize: 14,
    color: colors.claimNew,
  },
  text: {
    fontFamily: fonts.ui,
    fontSize: 13,
    color: colors.parchment,
    flex: 1,
  },
});
