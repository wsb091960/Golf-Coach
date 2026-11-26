/* Progressive enhancement: native forms still work without JavaScript. */
(() => {
  let draftDirty = false;
  const draftEditor = document.querySelector('[data-draft-editor]');
  draftEditor?.addEventListener('input', () => { draftDirty = true; });
  window.addEventListener('beforeunload', (event) => {
    if (draftDirty) { event.preventDefault(); event.returnValue = ''; }
  });
  const showError = (form, message) => {
    let error = form.querySelector('[data-form-error]');
    if (!error) {
      error = document.createElement('p');
      error.dataset.formError = '1'; error.className = 'oi-error';
      error.setAttribute('role', 'alert'); form.append(error);
    }
    error.hidden = false; error.textContent = message;
    return error;
  };
  for (const form of document.querySelectorAll('form[data-online]')) {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      if (form.dataset.busy === '1') return;
      if (draftDirty && form !== draftEditor) {
        showError(form, 'Save your lesson draft before continuing so your changes are kept.');
        return;
      }
      form.dataset.busy = '1';
      const data = new FormData(form);
      if (event.submitter?.name) data.append(event.submitter.name, event.submitter.value);
      let error = form.querySelector('[data-form-error]');
      if (!error) {
        error = document.createElement('p');
        error.dataset.formError = '1'; error.className = 'oi-error';
        error.setAttribute('role', 'alert'); form.append(error);
      }
      error.hidden = true;
      const buttons = [...form.querySelectorAll('button')];
      buttons.forEach(button => { button.disabled = true; });
      const progress = form.querySelector('progress');
      const xhr = new XMLHttpRequest();
      // A named action button can shadow HTMLFormElement.action.
      xhr.open('POST', form.getAttribute('action') || location.href);
      xhr.timeout = 600000;
      const unlock = () => {
        form.dataset.busy = '0';
        buttons.forEach(button => { button.disabled = false; });
      };
      const fail = (message) => {
        unlock(); error.hidden = false; error.textContent = message;
        if (progress) progress.hidden = true;
      };
      if (progress) {
        progress.hidden = false; progress.value = 0;
        xhr.upload.addEventListener('progress', event => {
          if (event.lengthComputable) progress.value = Math.round(event.loaded / event.total * 100);
          const status = form.querySelector('[data-upload-status]');
          if (status) status.textContent = progress.value >= 100 ? 'Upload received. Saving your swing…' : `Uploading… ${progress.value}%`;
        });
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300 && xhr.responseURL) {
          if (form === draftEditor) draftDirty = false;
          location.assign(xhr.responseURL);
          return;
        }
        let message = 'Your change could not be saved. Please try again.';
        try { const value = JSON.parse(xhr.responseText).detail; if (typeof value === 'string') message = value; } catch (_) {}
        fail(message);
      };
      xhr.onerror = xhr.ontimeout = () => fail('Connection interrupted. Your entries are still here. Reconnect and try again.');
      xhr.send(data);
    });
  }
  const openDetails = (selector, focus = false) => {
    const details = document.querySelector(selector);
    if (!details) return;
    details.open = true;
    details.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (focus) details.querySelector('textarea,select,input')?.focus({ preventScroll: true });
  };
  document.querySelector('[data-open-followup]')?.addEventListener('click', () => openDetails('#follow-up', true));
  document.querySelector('[data-open-email]')?.addEventListener('click', () => openDetails('#email-intake', true));
  document.querySelector('[data-open-invite]')?.addEventListener('click', () => openDetails('#invite-student', true));
  document.querySelector('[data-focus-message]')?.addEventListener('click', (event) => {
    event.preventDefault();
    document.querySelector('#questions')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    document.querySelector('#questions textarea')?.focus({ preventScroll: true });
    history.replaceState(null, '', '#questions');
  });
  if (location.hash === '#follow-up') openDetails('#follow-up');
  if (location.hash === '#email-intake') openDetails('#email-intake');
  if (location.hash === '#invite-student') openDetails('#invite-student');
  for (const button of document.querySelectorAll('[data-queue-filter]')) {
    button.addEventListener('click', () => {
      const selected = button.dataset.queueFilter;
      let count = 0;
      for (const row of document.querySelectorAll('[data-queue-status]')) {
        const status = row.dataset.queueStatus;
        const visible = selected === 'all' || (selected === 'review' ? ['submitted', 'in_review', 'needs_view', 'follow_up_due'].includes(status) : status === selected);
        row.hidden = !visible;
        if (visible) count++;
      }
      for (const filter of document.querySelectorAll('[data-queue-filter]')) {
        filter.classList.toggle('is-active', filter === button);
        filter.setAttribute('aria-pressed', String(filter === button));
      }
      const label = document.querySelector('[data-queue-count]');
      if (label) label.textContent = `${count} ${count === 1 ? 'review' : 'reviews'}`;
      const empty = document.querySelector('[data-queue-empty]');
      if (empty) empty.hidden = count !== 0;
    });
  }
  for (const input of document.querySelectorAll('[data-media-input]')) {
    let previewURL;
    input.addEventListener('change', () => {
      const panel = input.closest('form').querySelector('[data-media-preview]');
      if (!panel) return;
      if (previewURL) URL.revokeObjectURL(previewURL);
      panel.replaceChildren(); panel.hidden = true;
      const file = input.files[0];
      if (!file) return;
      const extension = file.name.split('.').pop().toLowerCase();
      const image = ['jpg', 'jpeg', 'png'].includes(extension);
      if (!image && !['mp4', 'mov', 'webm'].includes(extension)) {
        showError(input.closest('form'), 'Choose an MP4, MOV or WEBM video, or a JPG/PNG screenshot.');
        input.value = ''; return;
      }
      if (file.size > (image ? 10 : 100) * 1024 * 1024) {
        showError(input.closest('form'), image ? 'Choose an image under 10 MB.' : 'Choose a video under 100 MB.');
        input.value = ''; return;
      }
      previewURL = URL.createObjectURL(file);
      const media = document.createElement(image ? 'img' : 'video');
      media.src = previewURL; media.className = 'oi-video';
      if (image) media.alt = 'Selected swing screenshot preview';
      else { media.controls = true; media.playsInline = true; media.preload = 'metadata'; }
      const label = document.createElement('p'); label.className = 'oi-small';
      label.textContent = `${file.name} · ${(file.size / (1024 * 1024)).toFixed(1)} MB · Ready to upload`;
      panel.append(media, label); panel.hidden = false;
      const error = input.closest('form').querySelector('[data-form-error]');
      if (error) error.hidden = true;
    });
  }
  for (const video of document.querySelectorAll('video[src]')) {
    const unavailable = () => {
      if (video.nextElementSibling?.matches('[data-playback-help]')) return;
      const help = document.createElement('p');
      help.dataset.playbackHelp = '1'; help.className = 'oi-notice';
      help.textContent = 'This device cannot preview this video format. ';
      const download = document.createElement('a');
      download.href = video.getAttribute('src'); download.download = '';
      download.textContent = 'Download the original';
      help.append(download, ' or upload an MP4 copy.');
      video.after(help);
    };
    video.addEventListener('error', unavailable);
    if (video.error) unavailable();
  }
  document.querySelector('[data-copy-invite]')?.addEventListener('click', async () => {
    const field = document.querySelector('[data-invite-link]');
    const status = document.querySelector('[data-copy-status]');
    try {
      await navigator.clipboard.writeText(field.value);
      status.textContent = 'Access link copied. Share it privately with your student.';
    } catch (_) {
      field.focus(); field.select();
      status.textContent = 'Select and copy the access link above.';
    }
  });
})();
