# Agent Communication Interface Research

**Date**: 2026-03-15
**Goal**: Evaluate options for secure text/voice communication with an AI agent running on a Hetzner Linux VM, accessible from phone or any device.

---

## Executive Summary

After evaluating 10 messaging platforms, 4 voice processing options, and surveying existing personal AI assistant projects, the recommended approach is:

**Primary: Telegram Bot** — fastest to build, excellent mobile experience, voice messages built in, good security for single-user, rich formatting, free.

**Secondary (if E2E encryption is required): Self-hosted Matrix + maubot** — full control, E2E encryption, bridges to other platforms, but significantly more setup.

**Voice processing: Soniox (already integrated)** — you already have a working `transcribe_on_server()` function in `research-server.py`. Just pipe Telegram voice messages through it.

---

## 1. Telegram Bot API

### How It Works
- Create a bot via @BotFather in Telegram, receive an auth token
- Bot runs on your server, either polling for updates or receiving webhooks
- All communication over HTTPS

### Security
- **Not E2E encrypted** — Telegram server-side encrypted only (Telegram can read messages)
- **Auth**: Token-based. You can restrict the bot to only respond to your Telegram user ID (a simple `if update.message.from_user.id != YOUR_ID: return` check)
- **Webhook security**: Optional `secret_token` header verification
- **Practical security**: For a personal AI agent, server-side encryption is likely sufficient. The threat model is "can Telegram read my messages to my agent?" — probably acceptable for most use cases

### Voice Messages
- **Receive**: Telegram sends voice messages as OGG/Opus files. Bot receives a `Voice` object with `file_id`, `duration`, `mime_type`
- **Send**: Bot can send voice messages back via `send_voice()`
- **Processing flow**: Receive OGG → download via `getFile()` → pipe to Soniox or Whisper → process → respond

### Files & Images
- **Upload limit**: 50 MB (official API), 2 GB with local Bot API server
- **Download limit**: 20 MB (official API), unlimited with local Bot API server
- **Types**: Photos, documents, audio, video, stickers, animations
- **For your use case**: Screenshots, code files, images all work well

### Rich Text / Markdown
- Supports **MarkdownV2** and **HTML** parse modes
- Bold, italic, underline, strikethrough, spoiler, code, pre (with language), links
- Inline keyboards with callback buttons for interactive UI

### Message Length & Long Responses
- **Text**: 4096 characters per message
- **Captions**: 1024 characters
- **Workaround for long responses**: Split into multiple messages, or send as a document/file
- Agent returning multi-page results → split at paragraph boundaries or send as `.md` file attachment

### Push Notifications
- Native Telegram push notifications on iOS and Android — no extra setup needed
- Instant delivery

### Rate Limits
- Private chats: ~1 message/second (soft limit)
- Bulk: ~30 messages/second
- Very generous for single-user bot

### Latency
- Webhook mode: near-instant delivery (< 1 second)
- Polling mode: configurable, typically 1-2 second delay

### Cost
- **Free** — no API costs, no limits for personal use

### Setup Complexity
- **Very low** — 30 minutes to a working bot
- `pip install python-telegram-bot`
- ~50 lines of Python for a basic echo bot
- Library is fully async (asyncio-based)
- ConversationHandler for multi-turn dialogues

### Verdict: STRONGLY RECOMMENDED
Best balance of ease, features, mobile experience, and voice support. The only downside is lack of E2E encryption.

---

## 2. Signal Bot / Signal CLI

### How It Works
- `signal-cli` is an unofficial command-line client for Signal
- Registers a phone number, sends/receives messages via Signal protocol
- Daemon mode with JSON-RPC or D-Bus interface for programmatic use

### Security
- **Full E2E encryption** — Signal protocol, the gold standard
- Only you and your agent can read messages

### Voice Messages
- **Poorly supported** — signal-cli documentation does not mention voice message handling
- Signal mobile sends voice as M4A files, but extracting them programmatically is undocumented

### Files & Images
- Attachment support exists but is not well-documented in signal-cli

### Rich Text
- Signal has very limited formatting — bold, italic, strikethrough, monospace
- No markdown rendering, no code blocks with syntax highlighting

### Push Notifications
- Native Signal notifications on iOS/Android

### Limitations
- **Must update every 3 months** — signal-cli releases older than 3 months may stop working due to Signal server changes
- **Requires JRE 25** — heavy dependency
- **Phone number required** — ties up a phone number for the bot
- **Fragile** — unofficial, can break with Signal server updates
- **No inline keyboards or interactive UI** — text only

### Cost
- Free (but requires a phone number)

### Setup Complexity
- **Medium-high** — JRE 25, registration with phone number, daemon setup, handle Signal's frequent protocol changes

### Verdict: NOT RECOMMENDED
Too fragile, poor voice support, limited formatting, high maintenance burden. E2E encryption is nice but not worth the tradeoffs for a personal agent.

---

## 3. Matrix / Element (Self-Hosted)

### How It Works
- Self-host a Matrix homeserver (Synapse or Conduit)
- Build a bot using `matrix-nio` (Python) or `maubot` (plugin framework)
- Use Element mobile app as the client
- Optionally bridge to Signal, Telegram, WhatsApp, iMessage, Discord, Slack

### Security
- **Full E2E encryption** — Megolm/Olm protocol
- **Self-hosted** — you control all data
- **Federation optional** — can run completely isolated

### Voice Messages
- Element supports voice messages with visual waveforms
- Bot receives audio attachments
- E2E encrypted file transfers supported in `matrix-nio[e2e]`

### Files & Images
- Full file sharing with E2E encryption
- No practical size limits on self-hosted server

### Rich Text
- Full HTML and Markdown support
- Code blocks, tables, everything

### Push Notifications
- Element has push notifications via Firebase/APNS (requires configuring push gateway)
- Self-hosted push can be tricky

### Bridging
Matrix has bridges for: Signal (mautrix-signal), Telegram (mautrix-telegram), WhatsApp (mautrix-whatsapp), iMessage (mautrix-imessage, requires Mac), Discord (4 bridges), Slack (4 bridges), SMS, IRC, XMPP, Instagram, and 15+ more.

This means you could set up Matrix as the hub and communicate with your agent via ANY of these platforms.

### Server Options
- **Synapse**: Reference implementation, Python, heavier (~500MB+ RAM for single user)
- **Conduit**: Rust, lightweight single binary, ~50MB RAM, beta but functional
- **Dendrite**: Go, lighter than Synapse, mostly feature-complete

### Bot Development
- **matrix-nio**: Python async library, E2E support with `[e2e]` extra, requires libolm
- **maubot**: Plugin-based bot framework, Docker deploy, E2E support, management web UI

### Message Length
- No hard limit in Matrix protocol
- Element displays long messages well

### Cost
- Free (self-hosted)
- ~100-200MB RAM for Conduit, ~500MB+ for Synapse

### Setup Complexity
- **High** — homeserver setup, domain/TLS, bot registration, E2E key management, push gateway
- With Docker: medium complexity, but still more moving parts than Telegram
- Bridging adds another layer of complexity per platform

### Verdict: RECOMMENDED IF E2E ENCRYPTION IS ESSENTIAL
The most powerful and flexible option. But the setup cost is 10-20x Telegram. Best approach: start with Telegram, migrate to Matrix later if needed. The bridge architecture means you could eventually use Matrix as the backend while still chatting via Telegram.

---

## 4. WhatsApp Business API

### How It Works
- Official Cloud API via Meta
- Requires Facebook Business account and business verification
- Phone number dedicated to the API

### Security
- E2E encrypted (WhatsApp protocol)
- But Meta processes metadata

### Voice Messages
- Supported — send and receive audio

### Cost
- **First 1,000 conversations/month free**, then per-conversation pricing
- Requires business verification (designed for businesses, not personal use)

### Limitations
- Business verification process is cumbersome for personal use
- 24-hour messaging window — after 24h of user inactivity, can only send template messages
- Template messages must be pre-approved by Meta
- Not designed for the personal AI agent use case

### Unofficial Alternative: whatsmeow
- Go library for WhatsApp Web multi-device API
- Can build bots, handles E2E encryption
- **Risk**: Account ban — WhatsApp actively detects and bans unofficial API usage
- Not recommended for a primary communication channel

### Verdict: NOT RECOMMENDED
Business API is overengineered for personal use. Unofficial APIs risk account bans. The 24-hour window is a dealbreaker for an agent that might need to send proactive messages.

---

## 5. iMessage from Linux

### Options Evaluated
1. **mautrix-imessage**: Matrix bridge, but **requires macOS** (reads iMessage database via AppleScript/SIP bypass)
2. **BlueBubbles Server**: Requires a Mac running as a server, forwards via Firebase
3. **pypush**: Reverse-engineered Apple Push Notification Service — **unstable, major rewrite in progress, not production-ready**
4. **AppleScript via SSH**: Could SSH to your Mac and use AppleScript to send/read iMessages

### The Reality
There is **no reliable way** to interface with iMessage from a Linux server. All approaches require either:
- A Mac always running as a relay
- Unofficial reverse-engineering that breaks regularly

### Verdict: NOT FEASIBLE
Unless you want to dedicate a Mac as a relay server, iMessage is not a viable option for a Linux-hosted agent.

---

## 6. Discord Bot

### How It Works
- Create a bot application in Discord Developer Portal
- Bot joins a private server (just you and the bot)
- Runs via WebSocket gateway or HTTP interactions

### Security
- Not E2E encrypted
- Discord has access to all messages
- Private server limits access to invited users only

### Voice
- Discord has voice channels, but bot voice requires complex audio streaming
- Voice messages (recorded clips) are a newer feature
- Bot receiving voice messages is possible but less well-documented than Telegram

### Rich Text
- Markdown support (bold, italic, code, code blocks)
- **Embeds**: Rich formatted cards with fields, images, colors, footers — excellent for structured agent responses
- 2000 character message limit (4000 with Nitro)

### Files
- 25 MB upload limit (free), 100 MB with Nitro

### Push Notifications
- Native push on mobile

### Cost
- Free

### Setup Complexity
- Low-medium. Good Python libraries (discord.py)

### Verdict: VIABLE BUT NOT OPTIMAL
The 2000 character limit is restrictive for agent responses. Embeds are nice but add complexity. Telegram is better in almost every way for this use case.

---

## 7. Slack (Personal Workspace)

### How It Works
- Create a free Slack workspace (just for you)
- Build a Slack app with bot functionality
- Socket Mode (no public endpoint needed) or HTTP events

### Security
- Not E2E encrypted
- Slack has access to all messages

### Voice
- No voice message support in Slack
- Audio/video clips exist in paid plans only

### Rich Text
- Block Kit: Very rich structured formatting (sections, fields, buttons, dropdowns)
- Markdown in blocks
- Good for structured agent responses

### Free Tier Limitations
- **90-day message history limit** — messages older than 90 days are hidden
- 1 workspace, up to 10 integrations
- No audio/video clips

### Message Limits
- 40,000 characters per message (generous)

### Push Notifications
- Native push on mobile

### Cost
- Free tier works but has the 90-day history limit
- Pro plan: $8.75/month/user

### Setup Complexity
- Medium — Slack app setup is more bureaucratic than Telegram

### Verdict: NOT RECOMMENDED
The 90-day message history limit on free tier is a dealbreaker. No voice messages on free tier. More setup than Telegram for fewer features.

---

## 8. Custom Web App (PWA)

### How It Works
- Build a chat web app with WebSocket real-time communication
- Service worker for push notifications
- Record audio in browser, upload to server
- Install as PWA on phone home screen

### Security
- Full control — your own TLS, auth, encryption
- Can implement E2E encryption if desired

### Voice
- `MediaRecorder` API for recording in browser
- Upload audio to server, process with Soniox/Whisper
- Can also do real-time streaming via WebSocket

### Rich Text
- Full control — render any HTML/Markdown/React components
- Can show code with syntax highlighting, charts, images, interactive elements

### Files
- Upload/download any file type and size

### Push Notifications (Critical Limitation)
- **iOS Safari**: Partial support since iOS 16.4, but:
  - Must add PWA to home screen first
  - Must be HTTPS
  - Requires user interaction to grant permission
  - Less reliable than native app push
  - **Some users report notifications not working consistently on iOS**
- **Android Chrome**: Full support
- **Desktop**: Full support (Chrome, Firefox, Edge, Safari 18+)

### Message Length
- No limits — full control

### Cost
- Free (self-hosted)

### Setup Complexity
- **High** — build the entire chat UI, WebSocket server, auth, push notification infrastructure, audio recording, service worker
- Could use ntfy (self-hosted push service) for notifications instead of Web Push API
- You already have a research-server.py that could be extended

### Verdict: VIABLE AS AN ENHANCEMENT, NOT PRIMARY
You already have a web app at `alifstian.duckdns.org:8084`. Adding a chat interface there is possible but is a lot of custom work. iOS push notifications are unreliable. Better to use Telegram for the messaging layer and the web app for rich UI when needed.

---

## 9. Email Interface

### How It Works
- Agent monitors an inbox (IMAP) or receives via webhook (Mailgun, SendGrid, Cloudflare Email Routing)
- Processes incoming emails, replies via SMTP
- Can handle attachments (images, files, voice recordings)

### Security
- TLS in transit, but email is fundamentally not secure
- No E2E encryption (unless using PGP, which is impractical)

### Voice
- Could attach voice recordings, but no native voice message UX
- Clunky compared to messaging apps

### Rich Text
- HTML emails — very rich formatting possible
- But email rendering is a minefield of compatibility issues

### Files
- Full attachment support (typically 25 MB limit per email)

### Push Notifications
- Email notifications are universal and reliable

### Latency
- **High** — polling interval for IMAP (1-5 minutes typical), plus email delivery delays
- Webhook-based receiving (Mailgun/SendGrid) is faster but adds a dependency

### Cost
- SMTP: Free (use server's sendmail or a service)
- Incoming webhook: Cloudflare Email Routing is free, Mailgun has a free tier

### Verdict: USEFUL AS A SECONDARY CHANNEL
Good for non-urgent notifications, daily digests, or long-form responses. Bad for interactive conversation. Consider as a complement to Telegram: agent sends you a daily summary email, or you can email it long documents to process.

---

## 10. SMS/MMS (Twilio)

### How It Works
- Twilio provides phone numbers that can send/receive SMS/MMS
- Webhook for incoming messages
- REST API for sending

### Security
- SMS is not encrypted at all
- Carrier can read messages

### Voice
- MMS supports audio attachments, but UX is poor
- Twilio also has voice call API (for actual phone calls)

### Files/Images
- MMS supports images (up to 5 MB typically)
- Limited compared to messaging apps

### Message Length
- SMS: 160 characters (concatenated up to ~1600)
- MMS: Varies by carrier

### Push Notifications
- SMS is the original push notification — always delivered

### Cost
- **Expensive** for an AI agent: ~$0.0079/SMS sent, ~$0.0075/SMS received (US)
- Phone number: ~$1.15/month
- International rates much higher
- A chatty agent could cost $5-20+/month

### Latency
- Near-instant delivery

### Verdict: NOT RECOMMENDED AS PRIMARY
Expensive, no encryption, tiny message limits, poor media support. Useful only as a fallback notification channel (e.g., "your server is down" alerts via SMS).

---

## Voice Processing Options

### A. Soniox (ALREADY INTEGRATED)

You already have a working `transcribe_on_server()` function in `research-server.py` that:
1. Uploads audio to Soniox API
2. Creates transcription with `stt-async-v4` model
3. Polls for completion
4. Returns transcript text
5. Supports all your languages (en, no, sv, da, it, de, es, fr, zh, id)

**Cost**: ~$0.10/hour of audio
**Latency**: Batch processing, typically 10-30 seconds for a voice message
**Quality**: Very good, handles code-switching between languages

**For Telegram integration**: Telegram voice → download OGG → convert to supported format → pipe through existing `transcribe_on_server()` → done.

### B. Whisper / whisper.cpp (Self-Hosted)

**Whisper (Python/PyTorch)**:
- Models: tiny (39M) → large (1.5B params)
- **CPU-only is slow**: ~10x realtime for tiny model, impractical for larger models without GPU
- Memory: 1-10 GB depending on model
- Your Hetzner VM likely has no GPU — would need to use tiny/base models
- Quality with tiny/base: mediocre, especially for non-English

**whisper.cpp (C++)**:
- Much lighter: tiny uses ~273 MB RAM, base ~388 MB, small ~852 MB
- CPU-optimized with OpenBLAS acceleration
- Built-in HTTP server: `whisper-server --host 127.0.0.1 -m model.bin`
- Better for CPU-only VPS than Python Whisper
- But accuracy with small models still below Soniox

**Verdict**: Unless you want to avoid API costs, stick with Soniox. The accuracy of self-hosted small Whisper models on multilingual voice notes will be significantly worse.

### C. Deepgram

- Cloud API, sub-300ms latency for real-time
- 45+ languages, very accurate (Nova-3 model)
- WebSocket streaming support
- Free tier available
- More expensive than Soniox for batch

**Verdict**: Good alternative if you need real-time streaming STT. For batch voice messages, Soniox is cheaper and already integrated.

### D. Voice Notes via Messaging Apps

| Platform | Voice Format | Bot Can Receive? | Bot Can Send? |
|----------|-------------|-----------------|---------------|
| Telegram | OGG/Opus | Yes (Voice object) | Yes (send_voice) |
| Signal | M4A | Poorly documented | Unknown |
| Discord | WebM/Opus | Yes (attachment) | Yes |
| WhatsApp | OGG/Opus | Yes (Cloud API) | Yes |
| Element/Matrix | OGG | Yes (attachment) | Yes |
| Slack | No voice msgs on free tier | N/A | N/A |
| iMessage | M4A/CAF | Not from Linux | N/A |

**Telegram is the clear winner** for voice message bot interaction.

---

## Existing Personal AI Assistant Projects

### Projects With Messaging Integrations

| Project | Telegram | Discord | Slack | WhatsApp | Matrix | Web | Voice |
|---------|----------|---------|-------|----------|--------|-----|-------|
| **Khoj** | Yes | Community | No | Yes | No | Yes | TTS |
| **Leon AI** | No | No | No | No | No | Custom | Yes (built-in) |
| **Home Assistant** | Yes | Yes | Yes | No | Yes | Yes | Yes (via add-ons) |
| **n8n** | Yes | Yes | Yes | Yes | Yes | Yes | Via nodes |
| **Open WebUI** | No | No | No | No | No | PWA | Yes (Whisper/Deepgram) |
| **LibreChat** | No | No | No | No | No | Web | Yes (OpenAI/Azure) |
| **Letta (MemGPT)** | No | No | No | No | No | API/CLI | No |

### Key Observations

1. **Telegram is the dominant choice** — Khoj, Home Assistant, and n8n all use Telegram as their primary mobile messaging interface
2. **Most projects use a simple bot pattern**: receive message → process → reply
3. **No project has solved the "perfect" multi-platform approach** — they each pick 1-3 platforms
4. **n8n is interesting as middleware**: It has pre-built nodes for Telegram, Discord, Slack, WhatsApp, Matrix, email, and can orchestrate AI agent workflows. Could be used as a routing layer.
5. **ntfy** is popular for push notifications in self-hosted projects — simple HTTP pub-sub, free, has iOS/Android apps

---

## Recommended Architecture

### Phase 1: Telegram Bot (Build This Week)

```
Phone (Telegram app)
    ↕ Telegram servers
    ↕ Webhook (HTTPS)
    ↕ Your Hetzner VM (research-server.py)
        ├── Text messages → Agent logic → Reply
        ├── Voice messages → Download OGG → Soniox transcribe → Agent logic → Reply
        ├── Images/files → Process → Reply
        └── Long responses → Split or send as file attachment
```

**Implementation sketch** (add to `research-server.py`):

```python
# New dependencies: python-telegram-bot
# Add webhook handler at /telegram-webhook

from telegram import Update
from telegram.ext import Application, MessageHandler, filters

YOUR_USER_ID = 123456789  # Your Telegram user ID

async def handle_message(update, context):
    if update.message.from_user.id != YOUR_USER_ID:
        return  # Ignore everyone else

    if update.message.voice:
        # Download voice, transcribe with existing transcribe_on_server()
        file = await update.message.voice.get_file()
        audio_path = await file.download_to_drive()
        text = transcribe_on_server(audio_path)
        # Process transcribed text...
    else:
        text = update.message.text

    # Route to your agent logic
    response = await process_agent_command(text)

    # Handle long responses
    if len(response) > 4000:
        # Send as file
        await update.message.reply_document(
            document=response.encode(),
            filename="response.md"
        )
    else:
        await update.message.reply_text(response, parse_mode='MarkdownV2')
```

**Security checklist**:
- Restrict bot to your user ID only
- Set webhook with `secret_token`
- Use HTTPS (you already have nginx)
- Don't expose bot token in client code

### Phase 2: Optional Enhancements

1. **ntfy for proactive notifications**: Agent can push notifications even when you haven't messaged it (e.g., "pipeline finished", "new article matched your interests")
2. **Email for long-form**: Agent sends daily digest or research results via email
3. **Matrix upgrade**: If you later want E2E encryption, set up Conduit + maubot, bridge Telegram via mautrix-telegram, keep using Telegram as the client while Matrix handles encryption and routing

### Why Not Start With Matrix?

Matrix is more powerful but:
- Synapse uses 500MB+ RAM (Conduit is lighter but beta)
- E2E key management adds complexity
- Push notifications require a push gateway
- Bridge setup is another layer
- Element mobile app is functional but less polished than Telegram
- Development iteration is slower (more moving parts)

For a personal agent where the threat model is "I don't want random people messaging my bot" (not "I need to hide from state actors"), Telegram's user ID restriction is sufficient.

---

## Comparison Matrix

| Criterion | Telegram | Matrix | Signal | Discord | Slack | Custom PWA | Email | SMS |
|-----------|----------|--------|--------|---------|-------|-----------|-------|-----|
| **E2E Encrypted** | No* | Yes | Yes | No | No | Possible | No | No |
| **Setup Time** | 30 min | 4-8 hrs | 2-4 hrs | 1 hr | 1-2 hrs | 8-20 hrs | 2-4 hrs | 1 hr |
| **Voice Messages** | Excellent | Good | Poor | OK | None (free) | Custom build | No | No |
| **File Sharing** | 50MB/2GB | Unlimited | Unknown | 25MB | Good | Unlimited | 25MB | 5MB |
| **Rich Text** | MD + HTML | Full HTML | Minimal | MD + Embeds | Block Kit | Full control | HTML | None |
| **Max Message** | 4096 chars | Unlimited | Unknown | 2000 chars | 40K chars | Unlimited | Large | 160 chars |
| **Push (iOS)** | Native | Via gateway | Native | Native | Native | Partial** | Native | Native |
| **Maintenance** | None | Medium | High | Low | Low | Medium | Low | Low |
| **Cost** | Free | Free | Free | Free | Free*** | Free | Free | ~$5/mo |
| **Long Responses** | Split/file | Native | Unknown | Split/embed | Native | Native | Native | No |
| **Mobile UX** | Excellent | Good | Good | Good | Good | Fair | Good | Fair |
| **Bot Ecosystem** | Mature | Growing | None | Mature | Mature | N/A | N/A | N/A |

\* Server-side encrypted, not E2E
\** iOS PWA push is partial/unreliable
\*** 90-day history limit on free Slack

---

## Final Recommendation

**Start with Telegram.** It covers 95% of the use case with 5% of the effort. You can have a working agent interface in an afternoon by extending your existing `research-server.py` with a Telegram webhook handler. Voice messages flow naturally through your existing Soniox pipeline.

If E2E encryption becomes important later, add a Matrix layer behind it — you can bridge Telegram to Matrix so you keep using the same client while gaining encryption on the server side.
