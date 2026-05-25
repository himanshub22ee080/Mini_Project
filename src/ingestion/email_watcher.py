import imaplib
import email
import os
import time
from src.core.config import EMAIL_HOST, EMAIL_USER, EMAIL_PASS, INCOMING_DIR

# File used to store the last processed UID so we only handle new messages
LAST_UID_FILE = os.path.join(INCOMING_DIR, ".last_email_uid")

def check_unseen_emails():
    """Connects to IMAP, checks unread emails, and downloads PDF attachments."""
    mail = None
    try:
        if not EMAIL_USER or not EMAIL_PASS:
            return  # Silently skip if email is not configured in .env

        # Connect to the server
        mail = imaplib.IMAP4_SSL(EMAIL_HOST)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # Use UID-based search so we can track which messages we've already
        # processed across runs. This avoids re-processing old unseen emails.
        status, data = mail.uid('search', None, 'UNSEEN')
        if status != 'OK':
            return

        uid_list = data[0].split() if data and data[0] else []
        if not uid_list:
            return

        # Read last processed UID. If missing, we treat current unseen set as
        # already-seen (first run) and record the highest UID without processing.
        last_uid = 0
        if os.path.exists(LAST_UID_FILE):
            try:
                with open(LAST_UID_FILE, 'r') as fh:
                    last_uid = int(fh.read().strip() or 0)
            except Exception:
                last_uid = 0

        # Convert UIDs to integers and sort ascending
        try:
            uids = sorted([int(u) for u in uid_list])
        except Exception:
            uids = []

        if not uids:
            return

        # If no checkpoint exists, initialize it to the latest unseen UID and
        # skip processing older unseen messages (user requested to track only
        # new incoming emails).
        if last_uid == 0 and not os.path.exists(LAST_UID_FILE):
            highest = max(uids)
            try:
                os.makedirs(INCOMING_DIR, exist_ok=True)
                with open(LAST_UID_FILE, 'w') as fh:
                    fh.write(str(highest))
                print(f"📧 Initialized last UID to {highest}. Skipping existing unseen emails.")
            except Exception as e:
                print(f"❌ Could not write last UID file: {e}")
            return

        # Filter to only UIDs strictly greater than last processed UID
        new_uids = [str(u) for u in uids if u > last_uid]
        if new_uids:
            print(f"📧 Found {len(new_uids)} new unread email(s). Checking for PDFs...")

        max_processed = last_uid
        for uid in new_uids:
            # Fetch the email data by UID
            _, msg_data = mail.uid('fetch', uid, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    # Save email body (plain text if available, otherwise html)
                    try:
                        email_text = None
                        subject = msg.get('Subject', '')
                        sender = msg.get('From', '')
                        if msg.is_multipart():
                            for part in msg.walk():
                                ctype = part.get_content_type()
                                cdisp = str(part.get('Content-Disposition')) if part.get('Content-Disposition') else ''
                                # Prefer inline text/plain parts
                                if ctype == 'text/plain' and 'attachment' not in cdisp:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        charset = part.get_content_charset() or 'utf-8'
                                        try:
                                            email_text = payload.decode(charset, errors='replace')
                                        except Exception:
                                            email_text = payload.decode('utf-8', errors='replace')
                                        break
                            # fallback to html if no plain text found
                            if email_text is None:
                                for part in msg.walk():
                                    if part.get_content_type() == 'text/html':
                                        payload = part.get_payload(decode=True)
                                        if payload:
                                            charset = part.get_content_charset() or 'utf-8'
                                            try:
                                                email_text = payload.decode(charset, errors='replace')
                                            except Exception:
                                                email_text = payload.decode('utf-8', errors='replace')
                                            break
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                charset = msg.get_content_charset() or 'utf-8'
                                try:
                                    email_text = payload.decode(charset, errors='replace')
                                except Exception:
                                    email_text = payload.decode('utf-8', errors='replace')

                        if email_text:
                            try:
                                os.makedirs(INCOMING_DIR, exist_ok=True)
                                safe_filename = f"{int(time.time())}_email_{uid}.txt"
                                filepath = os.path.join(INCOMING_DIR, safe_filename)
                                with open(filepath, 'w', encoding='utf-8') as f:
                                    f.write(f"From: {sender}\nSubject: {subject}\n\n")
                                    f.write(email_text)
                                print(f"📥 Saved email body to: {safe_filename}")
                            except Exception as e:
                                print(f"❌ Failed saving email body: {e}")

                    except Exception as e:
                        print(f"❌ Error extracting email body: {e}")

                    # Walk through the email parts to find attachments (PDFs)
                    for part in msg.walk():
                        if part.get_content_maintype() == 'multipart':
                            continue
                        if part.get('Content-Disposition') is None:
                            continue

                        filename = part.get_filename()
                        if filename and filename.lower().endswith('.pdf'):
                            # Ensure unique filename to prevent overwrites
                            safe_filename = f"{int(time.time())}_{filename}"
                            filepath = os.path.join(INCOMING_DIR, safe_filename)

                            # Download and save the PDF
                            try:
                                os.makedirs(INCOMING_DIR, exist_ok=True)
                                with open(filepath, 'wb') as f:
                                    f.write(part.get_payload(decode=True))
                                print(f"📥 Downloaded attachment from email: {safe_filename}")
                            except Exception as e:
                                print(f"❌ Failed saving attachment: {e}")

            try:
                max_processed = max(max_processed, int(uid))
            except Exception:
                pass

        # Update checkpoint with the highest processed UID
        try:
            os.makedirs(INCOMING_DIR, exist_ok=True)
            with open(LAST_UID_FILE, 'w') as fh:
                fh.write(str(max_processed))
        except Exception as e:
            print(f"❌ Could not update last UID file: {e}")
    except Exception as e:
        print(f"❌ Email Watcher Error: {e}")
    finally:
        if mail is not None:
            try:
                mail.logout()
            except Exception:
                pass

def start_email_polling(interval_seconds=10):
    """Runs continuously in a background thread."""
    print(f"✉️  Email polling active. Checking inbox every {interval_seconds} seconds...")
    while True:
        check_unseen_emails()
        time.sleep(interval_seconds)