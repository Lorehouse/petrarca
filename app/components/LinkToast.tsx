import React, { useEffect, useRef } from 'react';
import { Text, Pressable, Animated, StyleSheet, Platform } from 'react-native';
import { colors, fonts } from '../design/tokens';
import { logEvent } from '../data/logger';

interface LinkToastProps {
  domain: string;
  articleId: string;
  onViewQueue: () => void;
  onDismiss: () => void;
}

export default function LinkToast({ domain, articleId, onViewQueue, onDismiss }: LinkToastProps) {
  const slideAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
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
      }).start(() => onDismiss());
    }, 3000);

    return () => clearTimeout(timer);
  }, []);

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
      <Text style={styles.text} numberOfLines={1}>
        Queued: {domain}
      </Text>
      <Text style={styles.check}>{' \u2713'}</Text>
      <Pressable
        onPress={() => {
          logEvent('link_toast_view_queue', { article_id: articleId });
          onViewQueue();
        }}
        hitSlop={8}
        style={styles.action}
      >
        <Text style={styles.actionText}>View Queue</Text>
      </Pressable>
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
    gap: 4,
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
  text: {
    fontFamily: fonts.ui,
    fontSize: 13,
    color: colors.parchment,
    flex: 1,
  },
  check: {
    fontFamily: fonts.ui,
    fontSize: 13,
    color: colors.claimNew,
  },
  action: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    minHeight: 32,
    justifyContent: 'center' as const,
  },
  actionText: {
    fontFamily: fonts.uiMedium,
    fontSize: 12,
    color: '#e8a080',
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
});
