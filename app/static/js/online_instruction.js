/* Progressive enhancement: native forms still work without JavaScript. */
(() => {
  for (const form of document.querySelectorAll('form[data-online]')) {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      if (form.dataset.busy === '1') return;
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
      xhr.open('POST', form.action || location.href);
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
        });
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300 && xhr.responseURL) {
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
