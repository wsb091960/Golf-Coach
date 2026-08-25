from __future__ import annotations
from collections import Counter
from datetime import date
from pathlib import Path
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.store import add_session, add_shot, delete_session, delete_shot, get_session, get_session_shots, get_student, list_sessions, list_students, update_session, update_shot
from app.video_store import list_session_videos

APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / 'templates'))
router = APIRouter(prefix='/sessions', tags=['Sessions'])

def require_session(session_id: str, db: Session) -> dict:
    session = get_session(session_id, db=db)
    if session is None: raise HTTPException(404, 'Session not found')
    return session

@router.get('', response_class=HTMLResponse, name='session_list')
def session_list(request: Request, student_id: str = '', db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name='sessions.html', context={
        'page_title':'Sessions', 'active_page':'sessions', 'students':list_students(db=db),
        'sessions':list_sessions(db=db, student_id=student_id or None), 'selected_student_id':student_id,
        'today':date.today().isoformat(),
    })

@router.post('', name='session_create')
def session_create(student_id: str = Form(...), session_date: str = Form(...), session_type: str = Form('Coaching Session'), name: str = Form(''), notes: str = Form(''), db: Session = Depends(get_db)):
    if get_student(student_id, db=db) is None: raise HTTPException(400, 'Please select a valid student')
    session = add_session({'student_id':student_id,'session_date':session_date,'session_type':session_type.strip() or 'Coaching Session','primary_club':'','name':name.strip(),'notes':notes.strip()}, db=db)
    return RedirectResponse(f"/sessions/{session['id']}", status_code=303)

@router.get('/{session_id}', response_class=HTMLResponse, name='session_detail')
def session_detail(request: Request, session_id: str, db: Session = Depends(get_db)):
    session = require_session(session_id, db)
    student = get_student(str(session.get('student_id','')), db=db)
    shots = get_session_shots(session_id, db=db)
    videos = list_session_videos(db, session_id)
    included = [s for s in shots if s.get('included', True)]
    club_counts = Counter(
        str(row.get('club')).strip()
        for row in included
        if str(row.get('club') or '').strip()
    )
    club_count = len(club_counts)
    dominant_club = club_counts.most_common(1)[0][0] if club_counts else None
    if club_count == 0:
        club_summary = '—'
    elif club_count == 1:
        club_summary = dominant_club
    else:
        club_summary = f'Mixed · {club_count} Clubs'
    def avg(field):
        vals=[]
        for row in included:
            v=row.get(field)
            if v is None: continue
            try: vals.append(float(v))
            except (TypeError,ValueError): pass
        return round(sum(vals)/len(vals),2) if vals else None
    return templates.TemplateResponse(request=request, name='session_detail.html', context={
        'page_title':'Session Performance','active_page':'sessions','session':session,'student':student,
        'session_shots':shots,'session_videos':videos,
        'session_metrics':{'shots':len(included),'club_count':club_count,'club_summary':club_summary,'dominant_club':dominant_club,'carry':avg('carry_distance'),'ball_speed':avg('ball_speed'),'club_speed':avg('club_speed'),'smash':avg('smash_factor'),'attack':avg('attack_angle'),'path':avg('club_path'),'face':avg('club_face')}
    })

@router.post('/{session_id}/update', name='session_update')
def session_update(session_id: str, session_date: str = Form(...), session_type: str = Form('Coaching Session'), name: str = Form(''), notes: str = Form(''), coaching_notes: str = Form(''), db: Session = Depends(get_db)):
    current=require_session(session_id,db)
    update_session(session_id, {'session_date':session_date,'session_type':session_type.strip(),'primary_club':current.get('primary_club',''),'name':name.strip(),'notes':notes.strip(),'coaching_notes':coaching_notes.strip()}, db=db)
    return RedirectResponse(f'/sessions/{session_id}?saved=1', status_code=303)

@router.post('/{session_id}/shots/{shot_id}/toggle', name='shot_toggle')
def shot_toggle(session_id: str, shot_id: str, included: str = Form('true'), db: Session = Depends(get_db)):
    require_session(session_id,db); update_shot(shot_id, {'included':included.lower() in {'true','1','yes','on'}}, db=db)
    return RedirectResponse(f'/sessions/{session_id}', status_code=303)

def _same_metric(left, right, tolerance: float = .0001) -> bool:
    if left in (None, '') and right in (None, ''):
        return True
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return str(left or '').strip().lower() == str(right or '').strip().lower()


def _recalculate_estimated_outcomes(shot: dict, *, carry: bool, total: bool, apex: bool, offline: bool) -> None:
    """Refresh visualization outcomes from edited launch inputs.

    These are display estimates, not measured launch-monitor results.
    """
    import math
    import re

    key = re.sub(r'[^a-z0-9]', '', str(shot.get('club') or '').lower())
    profiles = {
        'driver': (1.65, 13, 2600, .10), '3wood': (1.52, 15, 3600, .07),
        '5wood': (1.47, 17, 4300, .06), '7wood': (1.43, 19, 5000, .05),
        '3hybrid': (1.41, 17, 4200, .05), '4hybrid': (1.38, 18, 4700, .05),
        '5hybrid': (1.34, 19, 5200, .04), '3iron': (1.42, 15, 4000, .05),
        '4iron': (1.38, 17, 4500, .045), '5iron': (1.34, 19, 5200, .04),
        '6iron': (1.31, 21, 5900, .035), '7iron': (1.28, 23, 6800, .03),
        '8iron': (1.25, 25, 7600, .025), '9iron': (1.19, 27, 8400, .02),
        'pw': (1.11, 29, 9000, .015), 'pitchingwedge': (1.11, 29, 9000, .015),
        'gapwedge': (1.03, 31, 9500, .01), 'sandwedge': (.94, 33, 10000, .008),
        'lobwedge': (.86, 35, 10500, .005),
    }
    if key in profiles:
        factor, ideal_launch, ideal_spin, roll = profiles[key]
    elif 'hybrid' in key:
        factor, ideal_launch, ideal_spin, roll = (1.37, 18, 4700, .045)
    elif 'wood' in key:
        factor, ideal_launch, ideal_spin, roll = (1.47, 16, 4000, .06)
    elif 'wedge' in key:
        factor, ideal_launch, ideal_spin, roll = (1.02, 31, 9500, .01)
    else:
        factor, ideal_launch, ideal_spin, roll = (1.25, 23, 6800, .03)

    ball = shot.get('ball_speed')
    club = shot.get('club_speed')
    smash = shot.get('smash_factor')
    if ball is None and club is not None:
        ball = float(club) * float(smash or 1.30)
        shot['ball_speed'] = round(ball, 2)
    launch = shot.get('launch_angle')
    spin = shot.get('spin_rate')

    if carry:
        if ball is None:
            raise HTTPException(422, 'Ball Speed or Club Speed is required to recalculate estimated carry')
        launch_factor = 1.0 if launch is None else max(.82, min(1.04, 1 - abs(float(launch) - ideal_launch) * .008))
        spin_factor = 1.0 if spin is None else max(.86, min(1.02, 1 - abs(float(spin) - ideal_spin) / max(ideal_spin, 1) * .10))
        shot['carry_distance'] = round(float(ball) * factor * launch_factor * spin_factor, 2)

    carry_value = shot.get('carry_distance')
    if carry_value is None:
        return
    if total:
        adjusted_roll = roll
        if launch is not None:
            adjusted_roll *= max(.35, min(1.45, 1 - (float(launch) - ideal_launch) * .035))
        if spin is not None:
            adjusted_roll *= max(.35, min(1.35, 1 - (float(spin) - ideal_spin) / max(ideal_spin, 1) * .45))
        shot['total_distance'] = round(float(carry_value) * (1 + adjusted_roll), 2)
    if apex:
        launch_for_apex = max(3.0, float(launch if launch is not None else ideal_launch))
        shot['apex_height'] = round(max(12.0, float(carry_value) * math.tan(math.radians(launch_for_apex)) * .84), 1)
    if offline:
        start = shot.get('launch_direction')
        if start is None:
            start = shot.get('club_face') or 0
        start_yards = math.tan(math.radians(float(start))) * float(carry_value)
        influence = shot.get('face_to_path')
        if influence is None and shot.get('club_face') is not None and shot.get('club_path') is not None:
            influence = float(shot['club_face']) - float(shot['club_path'])
        if influence is None:
            influence = float(shot.get('spin_axis') or 0) / 2
        shot['offline_distance'] = round(start_yards + float(influence) * max(.4, float(carry_value) / 130), 2)


@router.post('/{session_id}/shots/{shot_id}/edit', name='shot_metrics_edit')
async def shot_metrics_edit(request: Request, session_id: str, shot_id: str, db: Session = Depends(get_db)):
    coaching_session = require_session(session_id, db)
    current = next((row for row in get_session_shots(session_id, db=db) if str(row.get('id')) == str(shot_id)), None)
    if current is None:
        raise HTTPException(404, 'Shot not found in this session')
    student = get_student(str(coaching_session.get('student_id', '')), db=db)
    form = await request.form()
    club = str(form.get('club') or '').strip()
    if not club:
        raise HTTPException(422, 'Club is required')
    labels = {
        'ball_speed':'Ball speed','club_speed':'Club speed','smash_factor':'Smash factor',
        'launch_angle':'Launch angle','launch_direction':'Start angle','spin_rate':'Spin rate',
        'spin_axis':'Spin axis','carry_distance':'Carry distance','total_distance':'Total distance',
        'apex_height':'Apex height','attack_angle':'Attack angle','club_path':'Club path',
        'club_face':'Club face','face_to_path':'Face-to-path','offline_distance':'Offline distance',
    }
    changes = {'club': club}
    for key, label in labels.items():
        changes[key] = _manual_number(form.get(key), label)

    speed_changed = any(not _same_metric(changes.get(key), current.get(key)) for key in ('ball_speed', 'club_speed'))
    smash_was_unchanged = _same_metric(changes.get('smash_factor'), current.get('smash_factor'))
    calculated_smash = None
    if changes['ball_speed'] is not None and changes['club_speed'] not in (None, 0):
        calculated_smash = changes['ball_speed'] / changes['club_speed']
    smash_inconsistent = calculated_smash is not None and (
        changes.get('smash_factor') is None or abs(float(changes['smash_factor']) - calculated_smash) > .015
    )
    if calculated_smash is not None and (changes['smash_factor'] is None or (speed_changed and smash_was_unchanged) or smash_inconsistent):
        changes['smash_factor'] = round(calculated_smash, 4)
    if changes['face_to_path'] is None and changes['club_face'] is not None and changes['club_path'] is not None:
        changes['face_to_path'] = round(changes['club_face'] - changes['club_path'], 4)

    estimated_source = 'estimated' in str(current.get('source') or '').lower()
    driver_changed = smash_inconsistent or str(club).strip().lower() != str(current.get('club') or '').strip().lower() or any(
        not _same_metric(changes.get(key), current.get(key))
        for key in ('ball_speed', 'club_speed', 'smash_factor', 'launch_angle', 'spin_rate')
    )
    carry_was_unchanged = _same_metric(changes.get('carry_distance'), current.get('carry_distance'))
    total_was_unchanged = _same_metric(changes.get('total_distance'), current.get('total_distance'))
    apex_was_unchanged = _same_metric(changes.get('apex_height'), current.get('apex_height'))
    offline_was_unchanged = _same_metric(changes.get('offline_distance'), current.get('offline_distance'))
    direction_changed = any(
        not _same_metric(changes.get(key), current.get(key))
        for key in ('launch_direction', 'spin_axis', 'club_path', 'club_face', 'face_to_path')
    )
    if estimated_source and (driver_changed or not carry_was_unchanged):
        _recalculate_estimated_outcomes(
            changes,
            carry=driver_changed and carry_was_unchanged,
            total=total_was_unchanged,
            apex=apex_was_unchanged,
            offline=offline_was_unchanged,
        )
    elif estimated_source and direction_changed and offline_was_unchanged:
        _recalculate_estimated_outcomes(changes, carry=False, total=False, apex=False, offline=True)

    changes['shot_shape'] = str(form.get('shot_shape') or '').strip()
    changes['shot_shape'] = _manual_shape_v2(
        changes,
        str(student.get('handedness', '') if student else ''),
        honor_explicit=True,
    )
    update_shot(shot_id, changes, db=db)
    return RedirectResponse(f'/sessions/{session_id}?shot_updated=1&selected_shot={shot_id}', status_code=303)

@router.post('/{session_id}/shots/{shot_id}/delete', name='shot_delete')
def shot_delete(session_id: str, shot_id: str, db: Session = Depends(get_db)):
    require_session(session_id,db); delete_shot(shot_id, db=db)
    return RedirectResponse(f'/sessions/{session_id}', status_code=303)

@router.post('/{session_id}/delete', name='session_delete')
def session_delete(session_id: str, db: Session = Depends(get_db)):
    require_session(session_id,db); delete_session(session_id, db=db)
    return RedirectResponse('/sessions', status_code=303)


def _manual_number(value, label: str):
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return round(float(text), 4)
    except ValueError as exc:
        raise HTTPException(422, f"{label} must be a number") from exc


def _manual_shape(shot: dict, handedness: str) -> str:
    explicit = str(shot.get("shot_shape") or "").strip()
    if explicit:
        return explicit
    carry = shot.get("carry_distance") or 100.0
    start = shot.get("launch_direction")
    if start is None:
        start = shot.get("club_face") or 0.0
    start_yards = __import__("math").tan(float(start) * __import__("math").pi / 180) * float(carry)
    offline = shot.get("offline_distance")
    if offline is not None:
        curve = float(offline) - start_yards
    elif shot.get("face_to_path") is not None:
        curve = float(shot["face_to_path"]) * max(.4, float(carry) / 130)
    elif shot.get("spin_axis") is not None:
        curve = float(shot["spin_axis"]) * max(.25, float(carry) / 180)
    else:
        curve = 0.0
    orientation = -1 if "left" in str(handedness or "").lower() else 1
    start *= orientation; curve *= orientation
    row = 0 if start < -1.5 else 2 if start > 1.5 else 1
    column = 0 if curve < -1.25 else 2 if curve > 1.25 else 1
    return [
        ["Pull Hook", "Pull Straight", "Pull Fade"],
        ["Hook", "Straight", "Slice"],
        ["Push Draw", "Push Straight", "Push Slice"],
    ][row][column]




def _manual_shape_v2(shot: dict, handedness: str, honor_explicit: bool = True) -> str:
    explicit=str(shot.get('shot_shape') or '').strip()
    if honor_explicit and explicit: return explicit
    carry=float(shot.get('carry_distance') or 100)
    start=shot.get('launch_direction')
    if start is None: start=shot.get('club_face') or 0
    start=float(start);start_yards=__import__('math').tan(start*__import__('math').pi/180)*carry
    offline=shot.get('offline_distance');ftp=shot.get('face_to_path')
    if ftp is None and shot.get('club_face') is not None and shot.get('club_path') is not None: ftp=float(shot['club_face'])-float(shot['club_path'])
    if offline is not None: curve=float(offline)-start_yards
    elif ftp is not None: curve=float(ftp)*max(.4,carry/130)
    elif shot.get('spin_axis') is not None: curve=float(shot['spin_axis'])*max(.25,carry/180)
    else: curve=0
    orientation=-1 if 'left' in str(handedness or '').lower() else 1;start*=orientation;curve*=orientation
    start_zone='pull' if start < -1.5 else 'push' if start > 1.5 else 'center'
    if abs(curve)<=max(1.25,carry*.012): return 'Pull Straight' if start_zone=='pull' else 'Push Straight' if start_zone=='push' else 'Straight'
    severe=abs(curve)>=max(6.0,carry*.075) or (ftp is not None and abs(float(ftp))>=5.0) or (offline is None and shot.get('spin_axis') is not None and abs(float(shot['spin_axis']))>=10.0)
    curve_name=('Slice' if severe else 'Fade') if curve>0 else ('Hook' if severe else 'Draw')
    return ('Pull ' if start_zone=='pull' else 'Push ' if start_zone=='push' else '')+curve_name


@router.post('/{session_id}/shots/manual', name='manual_shot_create')
async def manual_shot_create(request: Request, session_id: str, db: Session = Depends(get_db)):
    coaching_session=require_session(session_id,db)
    student=get_student(str(coaching_session.get('student_id','')),db=db)
    form=await request.form()
    club=str(form.get('club') or '').strip()
    if not club: raise HTTPException(422,'Club is required')
    labels={
        'ball_speed':'Ball speed','club_speed':'Club speed','smash_factor':'Smash factor',
        'launch_angle':'Launch angle','launch_direction':'Start angle','spin_rate':'Spin rate',
        'spin_axis':'Spin axis','carry_distance':'Carry distance','total_distance':'Total distance',
        'apex_height':'Apex height','attack_angle':'Attack angle','club_path':'Club path',
        'club_face':'Club face','face_to_path':'Face-to-path','offline_distance':'Offline distance',
    }
    shot={'session_id':session_id,'student_id':str(coaching_session.get('student_id','')),'club':club,'source':'Manual Entry','included':True}
    for key,label in labels.items(): shot[key]=_manual_number(form.get(key),label)
    shot['shot_shape']=str(form.get('shot_shape') or '').strip()
    if shot['smash_factor'] is None and shot['ball_speed'] is not None and shot['club_speed'] not in (None,0):
        shot['smash_factor']=round(shot['ball_speed']/shot['club_speed'],4)
    if shot['face_to_path'] is None and shot['club_face'] is not None and shot['club_path'] is not None:
        shot['face_to_path']=round(shot['club_face']-shot['club_path'],4)
    shot['shot_shape']=_manual_shape_v2(shot,str(student.get('handedness','') if student else ''))
    add_shot(shot,db=db)
    return RedirectResponse(f'/sessions/{session_id}?manual_shot_added=1',status_code=303)
