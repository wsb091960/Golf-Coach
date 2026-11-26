"""Real browser pilot check, isolated synthetic database and media only.

Run: PLAYWRIGHT_EXECUTABLE_PATH=/path/to/chromium python tests/online_instruction_browser.py
Requires optional development dependencies playwright, httpx, uvicorn; ffmpeg and openssl.
No production services, credentials or student records are used.
"""
import base64
from datetime import timedelta
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
scratch = tempfile.TemporaryDirectory(prefix='golf-online-browser-')
work = Path(scratch.name)
sock = socket.socket()
sock.bind(('127.0.0.1', 0))
origin = f'https://localhost:{sock.getsockname()[1]}'
os.environ.update(DATABASE_URL='sqlite:///' + str(work / 'pilot.db'),
    ONLINE_INSTRUCTION_ENABLED='1', ONLINE_INSTRUCTION_MEDIA_DIR=str(work / 'media'),
    GOLF_PUBLIC_URL=origin)

from app.main import app
from app.database import SessionLocal
from app.models import Student
from app.online_instruction import StudentSession
from app.routers.auth import GolfSession, digest, now_utc, owner_email
import uvicorn
from playwright.sync_api import sync_playwright

with SessionLocal() as db:
    db.add_all([Student(id='demo-a', first_name='Alex', last_name='Demo'),
                Student(id='demo-b', first_name='Blair', last_name='Demo')])
    db.add(GolfSession(token_hash=digest('a' * 64), owner_email=owner_email(),
                       expires_at=now_utc() + timedelta(hours=1)))
    for sid, token in [('demo-a', 'b' * 64), ('demo-b', 'c' * 64)]:
        db.add(StudentSession(token_hash=digest(token), student_id=sid,
                              expires_at=now_utc() + timedelta(hours=1)))
    db.commit()

subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout',
    str(work / 'key.pem'), '-out', str(work / 'cert.pem'), '-days', '1', '-subj', '/CN=localhost'],
    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=640x360:rate=24',
    '-t', '2', '-c:v', 'libvpx-vp9', '-b:v', '180k', str(work / 'swing.webm')], check=True)
subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=640x360:rate=24',
    '-t', '2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(work / 'swing.mov')], check=True)
config = uvicorn.Config(app, log_level='error', lifespan='off',
    ssl_keyfile=str(work / 'key.pem'), ssl_certfile=str(work / 'cert.pem'))
server = uvicorn.Server(config)
thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
thread.start()
for _ in range(100):
    if server.started:
        break
    time.sleep(.1)
assert server.started, 'The isolated test server did not start'

output = Path(os.environ.get('ONLINE_QA_OUTPUT', str(work / 'screenshots')))
output.mkdir(parents=True, exist_ok=True)
errors = []

def cookie(name, value):
    return dict(name=name, value=value, url=origin, secure=True, httpOnly=True, sameSite='Lax')


def no_overflow(page):
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), page.url


try:
    with sync_playwright() as p:
        options = dict(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        if os.environ.get('PLAYWRIGHT_EXECUTABLE_PATH'):
            options['executable_path'] = os.environ['PLAYWRIGHT_EXECUTABLE_PATH']
        browser = p.chromium.launch(**options)
        student = browser.new_context(ignore_https_errors=True, viewport={'width': 390, 'height': 844}, is_mobile=True)
        student.add_cookies([cookie('__Host-golf_student', 'b' * 64)])
        page = student.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(origin + '/learn')
        no_overflow(page)
        page.get_by_role('link', name='Upload a swing', exact=True).click()
        page.get_by_label('What would you like to improve?').fill('Build a consistent driver start line.')
        page.get_by_label('Club', exact=True).fill('Driver')
        page.get_by_label('Handedness').select_option('Right')
        page.get_by_label('Typical miss').fill('Starts left and fades back.')
        page.get_by_role('button', name='Continue to swing upload').click()
        page.wait_for_url('**/learn/submissions/*')
        identity = page.url.rsplit('/', 1)[-1]
        page.locator('[data-media-input]').set_input_files(str(work / 'swing.webm'))
        assert page.locator('[data-media-preview] video').is_visible()
        page.get_by_role('button', name='Upload swing', exact=True).click()
        page.get_by_role('button', name='Submit for coaching review').wait_for()
        page.get_by_role('button', name='Submit for coaching review').click()
        page.get_by_text('Your swing is with William.', exact=False).wait_for()

        coach_context = browser.new_context(ignore_https_errors=True, viewport={'width': 1440, 'height': 1000})
        coach_context.add_cookies([cookie('__Host-golf_session', 'a' * 64)])
        coach = coach_context.new_page()
        coach.on('pageerror', lambda error: errors.append(str(error)))
        coach.goto(origin + '/online-instruction')
        coach.get_by_role('button', name='Lesson ready', exact=True).click()
        assert coach.locator('[data-queue-empty]').is_visible()
        coach.get_by_role('button', name='To review', exact=True).click()
        assert coach.locator('[data-queue-status]:visible').count() == 1
        coach.screenshot(path=str(output / 'coach-queue.png'), full_page=True)
        coach.locator('.oi-queue-row').first.click()
        coach.get_by_label('Student summary', exact=True).fill('Begin with alignment and check the start line before adding another change.')
        coach.get_by_label('One main priority', exact=True).fill('Aim the face first. Then set your feet.')
        coach.get_by_label('Priority drills and practice instructions').fill('Use an alignment stick. Rehearse your setup five times, then hit ten shots.')
        coach.get_by_label('Measurable practice test').fill('Track 10 shots through a start-line gate.')
        coach.get_by_text('Private coach notes', exact=True).click()
        coach.get_by_label('Visible only to you').fill('PRIVATE-SYNTHETIC-NOTE')
        coach.get_by_role('button', name='Update status').click()
        coach.get_by_text('Save your lesson draft before continuing so your changes are kept.').wait_for()
        coach.get_by_role('button', name='Save draft', exact=True).click()
        coach.wait_for_url('**message=Lesson+draft+saved.')
        page.reload()
        assert 'PRIVATE-SYNTHETIC-NOTE' not in page.content()
        assert 'Aim the face first.' not in page.content()
        coach.get_by_label('Analysis video').set_input_files(str(work / 'swing.webm'))
        coach.get_by_role('button', name='Upload recording', exact=True).click()
        coach.wait_for_url('**message=Recording+uploaded.**')
        coach.get_by_role('button', name='Publish lesson', exact=True).click()
        coach.wait_for_url('**message=Lesson+published+to+student.')
        coach.screenshot(path=str(output / 'coach-review-desktop.png'), full_page=True)
        page.reload()
        page.get_by_role('heading', name='Your driver lesson', exact=True).wait_for()
        assert 'PRIVATE-SYNTHETIC-NOTE' not in page.content()
        video = page.locator('.oi-video--lesson')
        video.evaluate('(v)=>new Promise((resolve,reject)=>{if(v.readyState>=1)return resolve();v.onloadedmetadata=resolve;v.onerror=()=>reject(new Error("media metadata failed"));})')
        assert video.evaluate('(v)=>v.duration') >= 1
        video.evaluate('(v)=>{v.muted=true;return v.play();}')
        video.evaluate('(v)=>{v.pause();v.currentTime=1;}')
        assert video.evaluate('(v)=>v.currentTime') >= .9
        for width, height, name in [(390,844,'phone'), (820,1180,'tablet'), (1440,1000,'desktop')]:
            page.set_viewport_size(dict(width=width,height=height))
            no_overflow(page)
            page.screenshot(path=str(output / f'student-lesson-{name}.png'), full_page=True)
            coach.set_viewport_size(dict(width=width,height=height))
            no_overflow(coach)
        page.get_by_role('link', name='Ask William', exact=True).click()
        assert page.locator('#questions textarea').evaluate('(e)=>e===document.activeElement')
        page.get_by_label('Your message').fill('Practiced 20 balls. Start line improved.')
        page.get_by_role('button', name='Send to William', exact=True).click()
        page.get_by_text('Practiced 20 balls. Start line improved.', exact=True).wait_for()
        page.get_by_role('link', name='Send follow-up swing', exact=True).click()
        assert page.locator('#follow-up').get_attribute('open') is not None
        page.get_by_label('Practice completed and results').fill('Twenty practice shots; ready to compare.')
        page.get_by_role('button', name='Start follow-up', exact=True).click()
        page.wait_for_url(lambda url: '/learn/submissions/' in url and identity not in url)
        page.locator('[data-media-input]').set_input_files(str(work / 'swing.mov'))
        page.get_by_role('button', name='Upload swing', exact=True).click()
        page.get_by_role('button', name='Submit for coaching review').wait_for()
        assert page.get_by_role('link', name='View the earlier lesson').is_visible()
        # Verify the MOV original's MIME/range delivery, even on Linux builds
        # without the codec used by a particular iPhone camera setting.
        source = page.locator('#swing-evidence video').get_attribute('src')
        response = student.request.get(origin + source, headers={'Range': 'bytes=0-31'})
        assert response.status == 206
        assert response.headers['content-type'] == 'video/quicktime'
        other = browser.new_context(ignore_https_errors=True)
        other.add_cookies([cookie('__Host-golf_student', 'c' * 64)])
        assert other.request.get(origin + '/learn/submissions/' + identity).status == 404
        assert other.request.get(origin + '/online-instruction').status == 401
        # Email-first entry: a public visitor starts without a code; the coach
        # manually imports their email attachments before issuing portal access.
        newcomer = browser.new_context(ignore_https_errors=True, viewport={'width': 390, 'height': 844})
        inquiry = newcomer.new_page()
        inquiry.on('pageerror', lambda error: errors.append(str(error)))
        inquiry.goto(origin + '/')
        inquiry.get_by_role('link', name='Send William Your Swing').click()
        for width, height, name in [(390,844,'phone'), (820,1180,'tablet'), (1440,1000,'desktop')]:
            inquiry.set_viewport_size(dict(width=width,height=height))
            no_overflow(inquiry)
            assert inquiry.get_by_role('link', name='Email William your swing').get_attribute('href').startswith('mailto:')
            inquiry.screenshot(path=str(output / f'email-entry-{name}.png'), full_page=True)
        coach.goto(origin + '/online-instruction')
        coach.set_viewport_size(dict(width=390,height=844))
        coach.get_by_role('link', name='Add email inquiry', exact=True).click()
        coach.get_by_label('First name (new golfer)', exact=True).fill('Casey')
        coach.get_by_label('Last name (new golfer, optional)', exact=True).fill('Demo')
        coach.get_by_label('Sender email', exact=True).fill('casey@example.com')
        coach.get_by_label('What would the golfer like help with?').fill('Improve driver contact.')
        coach.get_by_text('Private email reference', exact=True).click()
        coach.get_by_label('Source note (coach only)').fill('PRIVATE-EMAIL-REFERENCE')
        no_overflow(coach)
        coach.screenshot(path=str(output / 'email-intake-phone.png'), full_page=True)
        coach.get_by_role('button', name='Save inquiry and add attachments', exact=True).click()
        coach.wait_for_url(re.compile(re.escape(origin) + r'/online-instruction/[a-f0-9-]{36}$'))
        coach.get_by_role('heading', name='Continue from their first swing.', exact=True).wait_for()
        coach.screenshot(path=str(output / 'email-import-phone.png'), full_page=True)
        imported_id = coach.url.rsplit('/', 1)[-1]
        coach.get_by_label('Camera view', exact=True).select_option('Down-the-line')
        coach.get_by_label('Email attachment', exact=True).set_input_files(str(work / 'swing.webm'))
        assert coach.locator('[data-media-preview] video').is_visible()
        coach.get_by_role('button', name='Save email attachment', exact=True).click()
        coach.wait_for_url('**message=Email+attachment+saved.')
        coach.get_by_role('button', name='Add swing to review queue', exact=True).click()
        coach.wait_for_url('**message=Swing+added+to+review+queue.')
        coach.get_by_label('Student summary', exact=True).fill('We will start with setup.')
        coach.get_by_label('One main priority', exact=True).fill('Check your ball position.')
        coach.get_by_label('Priority drills and practice instructions').fill('Rehearse setup, then hit ten balls.')
        coach.get_by_label('Measurable practice test').fill('Count ten centered strikes.')
        coach.get_by_role('button', name='Publish lesson', exact=True).click()
        coach.wait_for_url('**message=Lesson+published+to+student.')
        for width, height in [(390,844), (820,1180), (1440,1000)]:
            coach.set_viewport_size(dict(width=width,height=height))
            no_overflow(coach)
        coach.get_by_role('button', name='Create this golfer’s private access link', exact=True).click()
        coach.get_by_role('link', name='Open invitation email draft').wait_for()
        invite_url = coach.locator('[data-invite-link]').input_value()
        inquiry.goto(invite_url)
        inquiry.get_by_role('button', name='Open my coaching space', exact=True).click()
        inquiry.wait_for_url('**/learn')
        inquiry.goto(origin + '/learn/submissions/' + imported_id)
        inquiry.get_by_text('Check your ball position.', exact=True).wait_for()
        assert inquiry.locator('#swing-evidence video').count() == 1
        assert 'PRIVATE-EMAIL-REFERENCE' not in inquiry.content()
        assert newcomer.request.get(origin + '/online-instruction').status == 401
        assert other.request.get(origin + '/learn/submissions/' + imported_id).status == 404
        print('PASS: public email entry, coach import, private source notes, publication, invitation, and original evidence visible without re-upload.')
        assert not errors, errors
        browser.close()
        print('PASS: complete browser lesson cycle, uploads, preview, filters, private drafts, publication, playback/seek, questions and follow-up.')
        print('PASS: phone/tablet/desktop layout, MOV range delivery, and cross-student denial; no browser JavaScript errors.')
        print('Screenshots:', output)
except Exception:
    for name in ['page', 'coach', 'inquiry']:
        active = locals().get(name)
        if active:
            try:
                active.screenshot(path=str(output / f'failure-{name}.png'), full_page=True)
                print('Failure page:', name, active.url)
            except Exception:
                pass
    raise
finally:
    server.should_exit = True
    thread.join(timeout=10)
    sock.close()
    scratch.cleanup()
