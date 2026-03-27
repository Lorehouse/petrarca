/**
 * Shared link component for markdown content.
 * Handles the web vs native split in one place:
 * - Web: native <a href target="_blank"> for navigation, onClick for side-effects
 * - Native: onPress + Linking.openURL
 *
 * This avoids a React Native Web pitfall where <Text onPress + href> causes
 * RNW to preventDefault on the anchor, then Linking.openURL uses window.open
 * which browsers block as a popup.
 */
import React from 'react';
import { Text, Linking, Platform, StyleSheet } from 'react-native';
import { logEvent } from '../data/logger';

const isWeb = Platform.OS === 'web';

export interface LinkIngestState {
  status: 'processing' | 'queued' | 'failed';
  ingestId: string;
  articleId: string;
}

export interface MarkdownLinkProps {
  url: string;
  text: string;
  /** Style for the link text */
  style: any;
  /** Suffix character (e.g. ⊕ or ↗) */
  suffix?: string;
  /** Style for the suffix */
  suffixStyle?: any;
  /** Log event name for taps */
  logEventName?: string;
  /** Called when an ingestable link is clicked */
  onIngest?: (url: string) => void;
  /** Current ingest state for this URL */
  ingestState?: LinkIngestState;
  /** Styles for ingest badges */
  ingestBadgeStyles?: {
    processing?: any;
    queued?: any;
    failed?: any;
  };
}

export function MarkdownLink({
  url, text, style, suffix, suffixStyle,
  logEventName = 'link_tap',
  onIngest, ingestState, ingestBadgeStyles,
}: MarkdownLinkProps) {
  const canIngest = !!onIngest;

  const webProps = isWeb ? {
    accessibilityRole: 'link' as const,
    href: url,
    hrefAttrs: { target: '_blank', rel: 'noopener noreferrer' },
    onClick: (e: any) => {
      // Cmd+click (Mac) / Ctrl+click (Win/Linux): let browser open in new tab natively
      if (e.metaKey || e.ctrlKey) {
        logEvent(logEventName, { url, link_text: text?.slice(0, 80), action: 'open_external' });
        return;
      }
      if (canIngest && !ingestState) {
        logEvent(logEventName, { url, link_text: text?.slice(0, 80), action: 'ingest' });
        onIngest!(url);
        e.preventDefault();
      } else {
        logEvent(logEventName, { url, link_text: text?.slice(0, 80) });
      }
    },
  } as any : {};

  const nativeProps = !isWeb ? {
    onPress: () => {
      if (canIngest && !ingestState) {
        logEvent(logEventName, { url, link_text: text?.slice(0, 80), action: 'ingest' });
        onIngest!(url);
      } else {
        logEvent(logEventName, { url, link_text: text?.slice(0, 80) });
        Linking.openURL(url);
      }
    },
    onLongPress: () => {
      logEvent(logEventName, { url, link_text: text?.slice(0, 80), action: 'open' });
      Linking.openURL(url);
    },
  } : {};

  return (
    <Text>
      <Text
        style={[style, isWeb && webCursorStyle]}
        {...nativeProps}
        {...webProps}
      >
        {text}
      </Text>
      {suffix && <Text style={suffixStyle}>{suffix}</Text>}
      {ingestState?.status === 'processing' && ingestBadgeStyles?.processing && (
        <Text style={ingestBadgeStyles.processing}>{' processing\u2026'}</Text>
      )}
      {ingestState?.status === 'queued' && ingestBadgeStyles?.queued && (
        <Text style={ingestBadgeStyles.queued}>{' queued \u2713'}</Text>
      )}
      {ingestState?.status === 'failed' && ingestBadgeStyles?.failed && (
        <Text style={ingestBadgeStyles.failed}>{' failed'}</Text>
      )}
    </Text>
  );
}

const webCursorStyle = { cursor: 'pointer' } as any;
