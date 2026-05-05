// Bucket list renderer — fetches /bucketlist.json and splits items into "todo" vs "done" lists.
// Order in items[] is the priority order; the admin (thirstypig.com/admin) writes the file.

(async function () {
  const todoOl = document.getElementById('bucketlist-todo');
  const doneUl = document.getElementById('bucketlist-done');
  const doneSection = document.getElementById('bucketlist-done-section');
  const updatedEl = document.getElementById('bucketlist-updated');
  const todoEyebrow = document.getElementById('bucketlist-todo-eyebrow');
  const doneEyebrow = document.getElementById('bucketlist-done-eyebrow');
  if (!todoOl) return;

  function fmtDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return '';
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  function renderItem(li, item, opts) {
    const name = document.createElement('strong');
    name.textContent = item.title;
    li.appendChild(name);
    if (item.note) {
      const note = document.createElement('span');
      note.style.color = 'var(--dim)';
      note.textContent = ' — ' + item.note;
      li.appendChild(note);
    }
    if (opts && opts.date && item.completed_date) {
      const when = document.createElement('span');
      when.style.color = 'var(--dim)';
      when.style.fontFamily = 'var(--mono)';
      when.style.fontSize = '11px';
      when.textContent = ' · ' + fmtDate(item.completed_date);
      li.appendChild(when);
    }
  }

  try {
    const res = await fetch('/bucketlist.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    const items = data.items || [];
    const todos = items.filter(i => i.status === 'todo');
    const done = items.filter(i => i.status === 'done');

    todoOl.innerHTML = '';
    if (todos.length) {
      todos.forEach(item => {
        const li = document.createElement('li');
        renderItem(li, item);
        todoOl.appendChild(li);
      });
      todoEyebrow.textContent = todos.length + ' item' + (todos.length === 1 ? '' : 's') + ' · in priority order';
    } else {
      todoOl.innerHTML = '<li style="color:var(--dim)">All done. Time to add more.</li>';
      todoEyebrow.textContent = '';
    }

    if (done.length) {
      done.forEach(item => {
        const li = document.createElement('li');
        renderItem(li, item, { date: true });
        doneUl.appendChild(li);
      });
      doneEyebrow.textContent = done.length + ' checked off';
      doneSection.hidden = false;
    }

    if (updatedEl && data.last_updated) {
      const d = new Date(data.last_updated);
      if (!isNaN(d)) {
        updatedEl.textContent = '// last updated ' + d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
      } else {
        updatedEl.textContent = '';
      }
    } else if (updatedEl) {
      updatedEl.textContent = '';
    }
  } catch (e) {
    console.warn('[bucketlist]', e);
    todoOl.innerHTML = '<li style="color:var(--dim)">Could not load the list right now.</li>';
    if (updatedEl) updatedEl.textContent = '';
  }
})();
