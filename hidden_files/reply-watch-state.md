# Apex reply-watch state
# Managed by the apex-reply-watch cron (hourly). Do not edit by hand.

last_covered_utc: 2026-10-07T03:35:22Z
twilio_approval_fired: false
fired_threads: []

# Notes
# - DFW HVAC blast: 15 personalized emails, subject "Exclusive DFW HVAC leads — $20 trial",
#   from sophieamoure2026@gmail.com, sent 2026-10-06 ~22:13–22:16 UTC. One bounced (AMS Adair).
# - Twilio: $20 funded 2026-10-06 ~21:43 UTC; Sole Proprietor A2P 10DLC registration under
#   review as of ~22:00 UTC. Blast script on Gary's Mac: /Users/sophieamoure/GG/titansignal_bots/apex_sms_blast.py
# - Deadline: 2026-10-09T22:30:00Z — schedule disables itself after this.
# - 2026-10-06T23:35Z: TrustHub rejected the Business Profile (error 18602 — Business ID
#   could not be verified), surfaced to Gary once. Do not fire the rejection again.
# - 2026-10-07T00:36Z run: no new Twilio mail, no contractor replies. Stayed silent.
# - 2026-10-07T02:37Z run: no Twilio mail at all in window (approval still pending,
#   TrustHub rejection already surfaced once — not re-fired). No contractor replies on the
#   DFW HVAC blast — subject search returned only the 16 self-sent blast messages. Window
#   triage: only self-sent outreach (roofing/electrician blasts), one mailer-daemon bounce,
#   Besser Part Sales promo, Pluto TV support mail — none reference Apex or the lead offer.
#   Stayed silent.
# - 2026-10-07T03:37Z run: no Twilio mail at all in window (approval still pending,
#   TrustHub rejection already surfaced once — not re-fired). No genuine replies on the
#   DFW HVAC blast — subject search returned only the 16 self-sent blast messages.
#   Window triage: mailer-daemon bounces, roofing-blast Zendesk/Gainsight-type auto-acks
#   (Gainsight ticket #506178 for Houston HVAC blast, Republic Services case
#   20261007-245818308 for roofing blast — both read and confirmed autoresponders, not
#   surfaced), plus support welcomes (magnolia.com, magazinesdirect.com, New Yorker,
#   LEVEL, RISE, Discord), Besser promo, Pluto TV — none reference a contractor reply
#   to the DFW HVAC blast. Stayed silent.
