"""Read-only Gmail inbox intake for Signal.

The poller observes mail and creates durable inbound events/tasks. It never marks
messages read, changes labels, creates ActionRequests, or grants reply authority.
"""
from __future__ import annotations

import base64, json, urllib.error, urllib.parse, urllib.request, uuid
from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Any

_PROFILE='https://gmail.googleapis.com/gmail/v1/users/{user}/profile'
_MESSAGES='https://gmail.googleapis.com/gmail/v1/users/{user}/messages'
_MESSAGE='https://gmail.googleapis.com/gmail/v1/users/{user}/messages/{mid}'
_HISTORY='https://gmail.googleapis.com/gmail/v1/users/{user}/history'

class GmailInboxBoundaryError(RuntimeError): pass
class GmailHistoryExpired(GmailInboxBoundaryError): pass

def _parse_time(value:str)->datetime:
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None: raise ValueError('timezone-aware timestamp required')
    return dt.astimezone(timezone.utc)
def _iso(dt): return dt.astimezone(timezone.utc).isoformat()
def _decode(data:str)->str:
    if not data:return ''
    raw=base64.urlsafe_b64decode(data+'='*((4-len(data)%4)%4))
    return raw.decode('utf-8','replace')
def _headers(payload:dict)->dict[str,str]:
    out={}
    for item in payload.get('headers') or []:
        if isinstance(item,dict) and item.get('name'):
            k=str(item['name']).lower(); out.setdefault(k,str(item.get('value') or '').strip())
    return out
def _plain(payload:dict)->str:
    if not isinstance(payload,dict):return ''
    if payload.get('mimeType')=='text/plain':
        text=_decode((payload.get('body') or {}).get('data') or '')
        if text:return text
    for part in payload.get('parts') or []:
        text=_plain(part)
        if text:return text
    return ''

def _attachments(payload:dict,limit:int=20)->list[dict[str,str]]:
    out=[]
    def walk(part):
        if not isinstance(part,dict) or len(out)>=limit:return
        body=part.get('body') or {};filename=str(part.get('filename') or '').strip();aid=str(body.get('attachmentId') or '').strip()
        if filename or aid:
            out.append({'filename':filename,'mime_type':str(part.get('mimeType') or ''),'attachment_id':aid})
        for child in part.get('parts') or []:walk(child)
    walk(payload);return out

class SignalGmailInboxPoller:
    def __init__(self, *, db, trigger_coordinator, account:str, access_token:str, urlopen=None,
                 timeout_seconds:int=30, max_pages:int=50, max_body_chars:int=32768):
        self.db=db; self.triggers=trigger_coordinator; self.account=(account or '').strip().lower(); self.token=(access_token or '').strip(); self._urlopen=urlopen or urllib.request.urlopen
        self.timeout=int(timeout_seconds); self.max_pages=int(max_pages); self.max_body_chars=int(max_body_chars)
        if '@' not in self.account: raise GmailInboxBoundaryError('explicit Gmail account required')
        if not self.token: raise GmailInboxBoundaryError('Gmail access token required')
        if self.max_pages<1 or self.max_body_chars<256: raise ValueError('invalid Gmail poll bounds')

    def _headers(self): return {'Authorization':f'Bearer {self.token}','Accept':'application/json','User-Agent':'stillpoint-core/signal-inbox'}
    def _get(self,url:str)->dict:
        req=urllib.request.Request(url,headers=self._headers(),method='GET')
        try:
            with self._urlopen(req,timeout=self.timeout) as r: raw=r.read()
        except urllib.error.HTTPError as exc:
            if exc.code==404 and '/history' in url: raise GmailHistoryExpired('Gmail history cursor expired') from exc
            raise GmailInboxBoundaryError(f'Gmail HTTP {exc.code}') from exc
        except (urllib.error.URLError,TimeoutError,OSError) as exc: raise GmailInboxBoundaryError(f'Gmail network failure: {type(exc).__name__}') from exc
        try:data=json.loads(raw.decode('utf-8'))
        except Exception as exc: raise GmailInboxBoundaryError('Gmail returned unreadable JSON') from exc
        if not isinstance(data,dict): raise GmailInboxBoundaryError('Gmail response must be object')
        return data

    def ensure_mailbox(self, *, now_iso:str):
        _parse_time(now_iso); c=self.db._connection()
        c.execute("""INSERT INTO signal_gmail_mailboxes(account,status,updated_at) VALUES(?,'active',?) ON CONFLICT(account) DO NOTHING""",(self.account,now_iso)); c.commit()

    def _profile(self):
        return self._get(_PROFILE.format(user=urllib.parse.quote(self.account,safe='')))

    def _message_ids(self)->list[str]:
        ids=[]; token=None
        for _ in range(self.max_pages):
            q=[('labelIds','INBOX'),('maxResults','100')]
            if token:q.append(('pageToken',token))
            data=self._get(_MESSAGES.format(user=urllib.parse.quote(self.account,safe=''))+'?'+urllib.parse.urlencode(q))
            for m in data.get('messages') or []:
                if isinstance(m,dict) and m.get('id') and str(m['id']) not in ids:ids.append(str(m['id']))
            token=data.get('nextPageToken')
            if not token:return ids
        raise GmailInboxBoundaryError('Gmail bootstrap exceeded max_pages; cursor not advanced')

    def _history_ids(self,start_history_id:str)->tuple[list[str],str]:
        ids=[]; token=None; end=None
        for _ in range(self.max_pages):
            q=[('startHistoryId',start_history_id),('historyTypes','messageAdded'),('labelId','INBOX'),('maxResults','100')]
            if token:q.append(('pageToken',token))
            data=self._get(_HISTORY.format(user=urllib.parse.quote(self.account,safe=''))+'?'+urllib.parse.urlencode(q))
            end=str(data.get('historyId') or end or '')
            for h in data.get('history') or []:
                for added in (h.get('messagesAdded') or []) if isinstance(h,dict) else []:
                    m=added.get('message') if isinstance(added,dict) else None
                    if isinstance(m,dict) and m.get('id') and ('INBOX' in (m.get('labelIds') or []) or not m.get('labelIds')):
                        mid=str(m['id']);
                        if mid not in ids:ids.append(mid)
            token=data.get('nextPageToken')
            if not token:
                if not end: raise GmailInboxBoundaryError('Gmail history response missing historyId')
                return ids,end
        raise GmailInboxBoundaryError('Gmail history exceeded max_pages; cursor not advanced')

    def _message(self,mid:str)->dict:
        url=_MESSAGE.format(user=urllib.parse.quote(self.account,safe=''),mid=urllib.parse.quote(mid,safe=''))+'?'+urllib.parse.urlencode({'format':'full'})
        return self._get(url)

    def _normalize(self,m:dict)->dict[str,Any]:
        payload=m.get('payload') or {}; h=_headers(payload); body=_plain(payload); truncated=len(body)>self.max_body_chars; body=body[:self.max_body_chars];attachments=_attachments(payload)
        return {
            'provider':'gmail','account':self.account,'message_id':str(m.get('id') or ''),'thread_id':str(m.get('threadId') or ''),'history_id':str(m.get('historyId') or ''),
            'internal_date_ms':str(m.get('internalDate') or ''),'from':h.get('from',''),'from_address':parseaddr(h.get('from',''))[1].lower(),'to':h.get('to',''),'cc':h.get('cc',''),
            'subject':h.get('subject',''),'date':h.get('date',''),'rfc822_message_id':h.get('message-id',''),'in_reply_to':h.get('in-reply-to',''),'references':h.get('references',''),'reply_to':h.get('reply-to',''),'auto_submitted':h.get('auto-submitted',''),'precedence':h.get('precedence',''),'list_unsubscribe':h.get('list-unsubscribe',''),
            'authentication_results':h.get('authentication-results',''),'return_path':h.get('return-path',''),
            'snippet':str(m.get('snippet') or ''),'text_plain':body,'text_plain_truncated':truncated,'has_attachments':bool(attachments),'attachments':attachments,
        }

    def _occurred(self,m:dict,now_iso:str)->str:
        try:return _iso(datetime.fromtimestamp(int(m.get('internalDate'))/1000,tz=timezone.utc))
        except Exception:return now_iso

    def _ingest(self,mid:str,*,now_iso:str)->int:
        m=self._message(mid); payload=self._normalize(m)
        if not payload['message_id']:raise GmailInboxBoundaryError('Gmail message missing id')
        event=self.triggers.ingest_event(source='gmail',event_type='message_received',dedupe_key=f'gmail:{self.account}:{payload["message_id"]}',occurred_at=self._occurred(m,now_iso),received_at=now_iso,payload=payload)
        return len(self.triggers.fire_event(event.event_id,now_iso=now_iso))

    def _receipt(self,*,mode,start,end,seen,tasks,status,started,finished,error=''):
        self.db._connection().execute("""INSERT INTO signal_gmail_poll_receipts(receipt_id,account,mode,started_at,finished_at,start_history_id,end_history_id,messages_seen,tasks_created,status,error) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            ('gmail-poll-'+uuid.uuid4().hex[:20],self.account,mode,started,finished,start,end,seen,tasks,status,error)); self.db._connection().commit()

    def poll(self, *, now_iso:str)->dict[str,Any]:
        _parse_time(now_iso); self.ensure_mailbox(now_iso=now_iso); c=self.db._connection(); row=c.execute('select * from signal_gmail_mailboxes where account=?',(self.account,)).fetchone()
        if row['status']=='paused': return {'status':'paused','messages_seen':0,'tasks_created':0}
        if row['status']=='resync_required': raise GmailHistoryExpired('mailbox requires explicit resync')
        start=str(row['history_id'] or ''); mode='history' if start else 'bootstrap'; begun=now_iso
        try:
            if mode=='bootstrap':
                profile=self._profile(); end=str(profile.get('historyId') or '')
                if not end:raise GmailInboxBoundaryError('Gmail profile missing historyId')
                ids=self._message_ids()
            else: ids,end=self._history_ids(start)
            tasks=sum(self._ingest(mid,now_iso=now_iso) for mid in ids)
            c.execute("""UPDATE signal_gmail_mailboxes SET history_id=?,status='active',bootstrap_completed_at=COALESCE(bootstrap_completed_at,?),last_polled_at=?,last_success_at=?,last_error=NULL,updated_at=? WHERE account=?""",
                (end,now_iso,now_iso,now_iso,now_iso,self.account)); c.commit(); self._receipt(mode=mode,start=start or None,end=end,seen=len(ids),tasks=tasks,status='succeeded',started=begun,finished=now_iso)
            return {'status':'succeeded','mode':mode,'messages_seen':len(ids),'tasks_created':tasks,'history_id':end}
        except GmailHistoryExpired as exc:
            c.execute("UPDATE signal_gmail_mailboxes SET status='resync_required',last_polled_at=?,last_error=?,updated_at=? WHERE account=?",(now_iso,str(exc),now_iso,self.account)); c.commit(); self._receipt(mode='history',start=start,end=start or None,seen=0,tasks=0,status='history_expired',started=begun,finished=now_iso,error=str(exc)); raise
        except Exception as exc:
            c.execute("UPDATE signal_gmail_mailboxes SET last_polled_at=?,last_error=?,updated_at=? WHERE account=?",(now_iso,f'{type(exc).__name__}: {exc}',now_iso,self.account)); c.commit(); self._receipt(mode=mode,start=start or None,end=start or None,seen=0,tasks=0,status='failed',started=begun,finished=now_iso,error=f'{type(exc).__name__}: {exc}'); raise

    def resync(self, *, now_iso:str)->dict[str,Any]:
        _parse_time(now_iso); self.ensure_mailbox(now_iso=now_iso); profile=self._profile(); end=str(profile.get('historyId') or '')
        if not end:raise GmailInboxBoundaryError('Gmail profile missing historyId')
        ids=self._message_ids(); tasks=sum(self._ingest(mid,now_iso=now_iso) for mid in ids); c=self.db._connection()
        prior=c.execute('select history_id from signal_gmail_mailboxes where account=?',(self.account,)).fetchone(); start=prior['history_id'] if prior else None
        c.execute("UPDATE signal_gmail_mailboxes SET history_id=?,status='active',bootstrap_completed_at=COALESCE(bootstrap_completed_at,?),last_polled_at=?,last_success_at=?,last_error=NULL,updated_at=? WHERE account=?",(end,now_iso,now_iso,now_iso,now_iso,self.account));c.commit()
        self._receipt(mode='resync',start=start,end=end,seen=len(ids),tasks=tasks,status='succeeded',started=now_iso,finished=now_iso)
        return {'status':'succeeded','mode':'resync','messages_seen':len(ids),'tasks_created':tasks,'history_id':end}
