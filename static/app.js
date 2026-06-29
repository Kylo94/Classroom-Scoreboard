// Inline score update handler.
document.addEventListener('click', async (event) => {
  const btn = event.target.closest('.score-btn');
  if (!btn) return;

  const card = btn.closest('.student-card');
  if (!card || !CLASS_ID) return;

  const studentId = card.dataset.studentId;
  const delta = parseInt(btn.dataset.delta, 10);

  // Optimistic UI: apply delta immediately so it feels instant.
  const display = card.querySelector('.score-display');
  const valueEl = card.querySelector('.score-value');
  const prev = parseInt(valueEl.textContent, 10);
  const next = prev + delta;
  valueEl.textContent = next;
  display.classList.toggle('positive', next > 0);
  display.classList.toggle('negative', next < 0);
  display.classList.remove('pulse');
  // Restart pulse animation.
  void display.offsetWidth;
  display.classList.add('pulse');

  const form = new FormData();
  form.append('delta', delta);

  try {
    const res = await fetch(
      `/classes/${CLASS_ID}/students/${studentId}/score`,
      { method: 'POST', body: form }
    );
    if (!res.ok) throw new Error('Update failed');
    const data = await res.json();
    // Sync with authoritative value from the server.
    valueEl.textContent = data.score;
    display.classList.toggle('positive', data.score > 0);
    display.classList.toggle('negative', data.score < 0);
  } catch (err) {
    // Revert on failure.
    valueEl.textContent = prev;
    display.classList.toggle('positive', prev > 0);
    display.classList.toggle('negative', prev < 0);
    alert('更新失败,请重试');
  }
});

// Remove a student via JS so the card can be deleted with a confirmation.
async function removeStudent(classId, studentId, name) {
  if (!confirm(`确定要移除学生「${name}」吗?`)) return;
  const form = new FormData();
  const res = await fetch(
    `/classes/${classId}/students/${studentId}/delete`,
    { method: 'POST', body: form, redirect: 'manual' }
  );
  // After delete the page is redirected server-side; just reload to reflect it.
  if (res.ok || res.status === 0) {
    window.location.reload();
  } else {
    alert('删除失败');
  }
}

// Inline rename: click the pencil button to edit, Enter to save, Esc to cancel.
function startRename(btn) {
  const card = btn.closest('.student-card');
  if (!card) return;
  const nameEl = card.querySelector('.student-name');
  if (!nameEl || nameEl.dataset.editing === 'true') return;

  const original = nameEl.dataset.original || nameEl.textContent.trim();

  nameEl.dataset.editing = 'true';
  nameEl.contentEditable = 'true';
  nameEl.textContent = original;
  nameEl.focus();

  // Select all text so the user can start typing immediately.
  const range = document.createRange();
  range.selectNodeContents(nameEl);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);

  const finish = async (commit) => {
    if (nameEl.dataset.editing !== 'true') return;
    nameEl.dataset.editing = 'false';
    nameEl.contentEditable = 'false';
    window.getSelection().removeAllRanges();

    const next = nameEl.textContent.trim();
    if (!commit || next === original || !next) {
      nameEl.textContent = original;
      return;
    }

    const studentId = card.dataset.studentId;
    const avatar = card.querySelector('.avatar');
    const form = new FormData();
    form.append('name', next);
    try {
      const res = await fetch(
        `/classes/${CLASS_ID}/students/${studentId}/rename`,
        { method: 'POST', body: form }
      );
      if (!res.ok) throw new Error('Rename failed');
      nameEl.dataset.original = next;
      nameEl.textContent = next;
      avatar.textContent = next.charAt(0).toUpperCase();
    } catch (err) {
      alert('改名失败,请重试');
      nameEl.textContent = original;
    }
  };

  const onBlur = () => finish(true);
  const onKey = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      nameEl.removeEventListener('blur', onBlur);
      finish(true);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      nameEl.removeEventListener('blur', onBlur);
      finish(false);
    }
  };

  nameEl.addEventListener('blur', onBlur);
  nameEl.addEventListener('keydown', onKey);
}

// ---------- Random student picker ----------

let pickerTimer = null;
let pickerSpinning = false;

function pickRandom() {
  return STUDENTS[Math.floor(Math.random() * STUDENTS.length)];
}

function openPicker() {
  if (!STUDENTS || STUDENTS.length === 0) return;
  const modal = document.getElementById('pickerModal');
  modal.classList.add('is-open');
  modal.setAttribute('aria-hidden', 'false');
  spinPicker();
}

function closePicker() {
  const modal = document.getElementById('pickerModal');
  modal.classList.remove('is-open', 'is-spinning', 'is-done');
  modal.setAttribute('aria-hidden', 'true');
  if (pickerTimer) {
    clearTimeout(pickerTimer);
    pickerTimer = null;
  }
  pickerSpinning = false;
  document.querySelectorAll('.student-card.is-picked')
    .forEach((el) => el.classList.remove('is-picked'));
  document.getElementById('pickerAgain').disabled = true;
}

function spinPicker() {
  if (!STUDENTS || STUDENTS.length === 0) return;
  const modal = document.getElementById('pickerModal');
  const nameEl = document.getElementById('pickerName');
  const avatarEl = document.getElementById('pickerAvatar');
  const hintEl = document.getElementById('pickerHint');
  const againBtn = document.getElementById('pickerAgain');

  document.querySelectorAll('.student-card.is-picked')
    .forEach((el) => el.classList.remove('is-picked'));

  modal.classList.add('is-spinning');
  modal.classList.remove('is-done');
  hintEl.textContent = '正在挑选幸运儿...';
  againBtn.disabled = true;

  const finalPick = pickRandom();
  let tickCount = 0;
  const totalTicks = 28;
  const baseDelay = 60;
  const maxDelay = 320;

  pickerSpinning = true;

  function tick() {
    if (!pickerSpinning) return;
    let flash;
    do {
      flash = STUDENTS[Math.floor(Math.random() * STUDENTS.length)];
    } while (flash.name === nameEl.textContent && STUDENTS.length > 1);
    nameEl.textContent = flash.name;
    avatarEl.textContent = flash.name.charAt(0).toUpperCase();

    tickCount++;
    if (tickCount < totalTicks) {
      const progress = tickCount / totalTicks;
      const delay = baseDelay + (maxDelay - baseDelay) * progress * progress;
      pickerTimer = setTimeout(tick, delay);
    } else {
      nameEl.textContent = finalPick.name;
      avatarEl.textContent = finalPick.name.charAt(0).toUpperCase();
      modal.classList.remove('is-spinning');
      modal.classList.add('is-done');
      hintEl.textContent = '请回答问题 🙋';
      againBtn.disabled = false;

      const card = document.querySelector(
        `.student-card[data-student-id="${finalPick.id}"]`
      );
      if (card) card.classList.add('is-picked');
      pickerSpinning = false;
    }
  }
  tick();
}

// Close modal on Escape key.
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    const modal = document.getElementById('pickerModal');
    if (modal && modal.classList.contains('is-open')) closePicker();
  }
});