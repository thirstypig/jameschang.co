// Bucket list renderer — fetches /bucketlist.json and splits items into "todo" vs "done" lists.
// Sort order: priority desc (high → medium → low → unset), then array order as tiebreaker.
// The admin on thirstypig.com/admin writes the file via the GitHub Contents API.

(async function () {
  const todoOl = document.getElementById('bucketlist-todo');
  const doneUl = document.getElementById('bucketlist-done');
  const doneSection = document.getElementById('bucketlist-done-section');
  const updatedEl = document.getElementById('bucketlist-updated');
  const todoEyebrow = document.getElementById('bucketlist-todo-eyebrow');
  const doneEyebrow = document.getElementById('bucketlist-done-eyebrow');
  if (!todoOl) return;

  const PRIORITY_RANK = { high: 0, medium: 1, low: 2 };
  const PRIORITY_COLOR = { high: 'var(--accent)', medium: 'var(--ink)', low: 'var(--dim)' };

  function fmtDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return '';
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  function chip(label, color) {
    const el = document.createElement('span');
    el.className = 'nb-chip';
    if (color) el.style.setProperty('--c', color);
    el.textContent = label;
    return el;
  }

  function sortByPriority(a, b) {
    const ra = PRIORITY_RANK[a.priority] ?? 99;
    const rb = PRIORITY_RANK[b.priority] ?? 99;
    if (ra !== rb) return ra - rb;
    return 0; // stable — preserves array order within priority bucket
  }

  function renderItem(li, item, opts) {
    const name = document.createElement('strong');
    name.textContent = item.title;
    li.appendChild(name);
    if (item.priority) {
      li.appendChild(chip(item.priority, PRIORITY_COLOR[item.priority]));
    }
    if (item.difficulty) {
      li.appendChild(chip(item.difficulty));
    }
    if (item.note) {
      const note = document.createElement('div');
      note.style.color = 'var(--dim)';
      note.style.fontSize = '13px';
      note.style.marginTop = '2px';
      note.textContent = item.note;
      li.appendChild(note);
    }
    if (opts && opts.date && item.completed_date) {
      const when = document.createElement('div');
      when.style.color = 'var(--dim)';
      when.style.fontFamily = 'var(--mono)';
      when.style.fontSize = '11px';
      when.style.marginTop = '2px';
      when.textContent = '✓ done ' + fmtDate(item.completed_date);
      li.appendChild(when);
    }
  }

  try {
    const res = await fetch('/bucketlist.json', { cache: 'reload' });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    const items = data.items || [];
    const todos = items.filter(i => i.status === 'todo').slice().sort(sortByPriority);
    const done = items.filter(i => i.status === 'done');

    todoOl.innerHTML = '';
    if (todos.length) {
      todos.forEach(item => {
        const li = document.createElement('li');
        li.style.marginBottom = '6px';
        renderItem(li, item);
        todoOl.appendChild(li);
      });
      todoEyebrow.textContent = todos.length + ' item' + (todos.length === 1 ? '' : 's') + ' · sorted by priority';
    } else {
      todoOl.innerHTML = '<li style="color:var(--dim)">All done. Time to add more.</li>';
      todoEyebrow.textContent = '';
    }

    if (done.length) {
      done.forEach(item => {
        const li = document.createElement('li');
        li.style.marginBottom = '6px';
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
