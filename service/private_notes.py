"""Plain-text personal notes, owned by an authenticated account, never a role."""
import base64,json,re
from datetime import datetime,timezone
from fastapi import Header,Query,Request
from pydantic import Field,field_validator
from .lesson import StrictModel

class NoteUpdate(StrictModel):
    revision:int=Field(ge=0,le=2**53-2)
    text:str=Field(max_length=8000)

    @field_validator('text')
    @classmethod
    def byte_bound(cls,value):
        if len(value.encode('utf-8'))>24000:
            raise ValueError('note exceeds UTF-8 byte bound')
        return value

def encode_cursor(row):
    raw=json.dumps([row['updated_at'],row['session_id']],separators=(',',':')).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')

def decode_cursor(value):
    try:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,256}',value):raise ValueError()
        at,sid=json.loads(base64.urlsafe_b64decode(value+'='*(-len(value)%4)))
        if not isinstance(at,str)or not isinstance(sid,str)or len(at)>40 or not re.fullmatch('[a-f0-9]{32}',sid):raise ValueError()
        if datetime.fromisoformat(at).isoformat()!=at:raise ValueError()
        return at,sid
    except Exception:
        raise ValueError('invalid notes cursor')from None

def register_routes(app,db,commit,authenticate,find_session,err):
    def load(c,sid,owner):
        row=c.execute('SELECT revision,text FROM participant_notes WHERE session_id=? AND participant_id=?',(sid,owner)).fetchone()
        return NoteUpdate(revision=row['revision'],text=row['text']).model_dump()if row else {'revision':0,'text':''}

    def identify(authorization,request):
        _,failure=authenticate(authorization,request)
        if failure is not None:return None,failure
        owner=getattr(request.state,'participant',None)
        if not owner:return None,err(403,'participant_login_required')
        return owner,None

    @app.get('/sessions/{sid}/notes')
    def read(sid:str,request:Request,authorization:str=Header(default='')):
        owner,failure=identify(authorization,request)
        if failure is not None:return failure
        c=db()
        try:
            if not find_session(c,sid,request):return err(404,'session_not_found')
            try:return load(c,sid,owner)
            except (ValueError,TypeError):return err(503,'private_notes_unavailable')
        finally:c.close()

    @app.post('/sessions/{sid}/notes')
    def save(sid:str,body:NoteUpdate,request:Request,authorization:str=Header(default='')):
        owner,failure=identify(authorization,request)
        if failure is not None:return failure
        if not request.headers.get('X-SOM-Participant'):return err(409,'participant_context_required')
        c=db()
        try:
            c.execute('BEGIN IMMEDIATE')
            if not find_session(c,sid,request):return err(404,'session_not_found')
            try:current=load(c,sid,owner)
            except (ValueError,TypeError):return err(503,'private_notes_unavailable')
            # A lost response can be replayed without a second revision. A
            # different stale edit must never overwrite this owner's new text.
            if current['text']==body.text:return current
            if current['revision']!=body.revision:return err(409,'private_notes_revision_conflict')
            revision=body.revision+1
            c.execute('INSERT INTO participant_notes(session_id,participant_id,revision,text,updated_at) VALUES(?,?,?,?,?) '
                      'ON CONFLICT(session_id,participant_id) DO UPDATE SET revision=excluded.revision,text=excluded.text,updated_at=excluded.updated_at',
                      (sid,owner,revision,body.text,datetime.now(timezone.utc).isoformat()))
            # No shared audit/heart event: even the note's existence is private.
            commit(c)
            return {'revision':revision,'text':body.text}
        finally:c.close()

    @app.get('/notes')
    def index(request:Request,cursor:str|None=Query(default=None,max_length=256),authorization:str=Header(default='')):
        owner,failure=identify(authorization,request)
        if failure is not None:return failure
        after='';params=[owner,owner]
        if cursor:
            try:at,sid=decode_cursor(cursor)
            except ValueError:return err(422,'invalid_notes_cursor')
            after='AND (n.updated_at<? OR (n.updated_at=? AND n.session_id<?))';params.extend([at,at,sid])
        c=db()
        try:
            rows=c.execute('SELECT n.*,s.maestro_alias,s.artist_alias,s.state FROM participant_notes n '
                           'JOIN sessions s ON s.id=n.session_id WHERE n.participant_id=? '
                           'AND EXISTS (SELECT 1 FROM session_members m WHERE m.session_id=s.id AND m.participant_id=?) AND n.text<>\'\' '+after+
                           ' ORDER BY n.updated_at DESC,n.session_id DESC LIMIT 21',params).fetchall()
            notes=[]
            try:
                for row in rows[:20]:
                    note=NoteUpdate(revision=row['revision'],text=row['text'])
                    notes.append({'session_id':row['session_id'],'revision':note.revision,'preview':note.text[:200],
                                  'updated_at':row['updated_at'],'maestro_alias':row['maestro_alias'],
                                  'artist_alias':row['artist_alias'],'state':row['state']})
            except (ValueError,TypeError):return err(503,'private_notes_unavailable')
            return {'notes':notes,'next_cursor':encode_cursor(rows[19])if len(rows)>20 else None}
        finally:c.close()
    return load
