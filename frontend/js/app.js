/**
 * ResumeAI Application Logic & UI Handlers
 */

// DOM Helpers
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = t => String(t ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const ring = (v, l) => `<div class="ring" style="--v:${+v || 0}"><div><b>${+v || 0}</b><small>${esc(l)}</small></div></div>`;
const bar = (l, v) => `<div class="mb-3"><div class="d-flex justify-content-between small"><span>${esc(l)}</span><b>${+v || 0}%</b></div><div class="bar"><i data-w="${+v || 0}"></i></div></div>`;
const list = (t, a, c = '') => Array.isArray(a) && a.length ? `<div class="col-md-6"><div class="cardx ${c}"><h6>${t}</h6><ul class="mb-0">${a.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div></div>` : '';
const chips = (a, c = '') => (a || []).map(x => `<span class="chip ${c}">${esc(x)}</span>`).join('');
const cap = s => s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ') : '';
const txt = v => Array.isArray(v) ? v.join(', ') : v;

const formatDate = (isoStr) => {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
};

// Tool Metadata
const TOOL_INFO = {
  analysis: {
    title: 'Resume Analysis',
    desc: 'Get a score with strengths, weaknesses and detailed feedback.'
  },
  ats: {
    title: 'ATS Compatibility Checker',
    desc: 'Rule-based formatting checks plus TF-IDF keyword evaluation.'
  },
  match: {
    title: 'Job Description Matching',
    desc: 'Paste a job description and see how well your resume fits.'
  },
  improve: {
    title: 'Resume Improvement Suggestions',
    desc: 'Get keyword and structure suggestions to improve your resume.'
  }
};

// Result Renderers
const R = {
  analysis: (d, s) => `<div class="row g-3 mb-3"><div class="col-md-4"><div class="cardx text-center"><h6>Overall Score</h6>${ring(s, '/ 100')}</div></div>
<div class="col-md-8"><div class="cardx"><canvas id="ch" height="130"></canvas></div></div></div>
<div class="row g-3 mb-3"><div class="col-md-5"><div class="cardx">${Object.entries(d.scores || {}).map(([k, v]) => bar(cap(k), v)).join('')}</div></div>
<div class="col-md-7"><div class="cardx"><h6>Detailed Feedback</h6><p class="mb-0">${esc(d.feedback)}</p></div></div></div>
<div class="row g-3 mb-3">${list('✅ Strengths', d.strengths, 'ok')}${list('⚠️ Weaknesses', d.weaknesses, 'bad')}${list('Missing Information', d.missing)}${list('Areas Requiring Improvement', d.improvements)}</div>
<div class="row g-3">${Object.entries(d.sections || {}).map(([k, v]) => `<div class="col-md-4"><div class="cardx"><h6>${esc(cap(k))}</h6><p class="small mb-0">${esc(txt(v))}</p></div></div>`).join('')}</div>`,

  ats: (d, s) => {
    const r = d.rule || {};
    return `<div class="row g-3 mb-3"><div class="col-md-4"><div class="cardx text-center"><h6>ATS Score</h6>${ring(s, '/ 100')}<span class="chip mt-2">${esc(d.status || '')}</span></div></div>
<div class="col-md-8"><div class="cardx"><h6>Formatting &amp; structure checks</h6>${(r.checks || []).map(c => `<div class="d-flex gap-2 mb-2"><i class="bi ${c.ok ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'}"></i><div><b>${esc(c.name)}</b><div class="small text-muted">${esc(c.detail)}</div></div></div>`).join('')}</div></div></div>
<div class="cardx mb-3" style="height:auto"><h6>Missing sections</h6>${chips(r.missing, 'bad') || '<span class="text-success">None — all core sections found 🎉</span>'}</div>
<div class="row g-3">${list('Detected Issues', d.semantic_issues, 'bad')}${list('Keyword Optimization', d.keyword_suggestions)}${list('Actionable Recommendations', d.recommendations, 'ok')}</div>
<p class="small text-muted mt-3">This is an estimate (60% rule-based, 40% TF-IDF). It does not guarantee compatibility with every ATS.</p>`;
  },

  match: (d, s) => `<div class="row g-3 mb-3"><div class="col-md-4"><div class="cardx text-center"><h6>Job Match</h6>${ring(s, '% match')}</div></div>
<div class="col-md-8"><div class="cardx"><canvas id="ch" height="120"></canvas></div></div></div>
<div class="row g-3 mb-3"><div class="col-md-6"><div class="cardx"><h6>Matching skills</h6>${chips(d.matching_skills, 'good') || '—'}</div></div>
<div class="col-md-6"><div class="cardx"><h6>Missing skills</h6>${chips(d.missing_skills, 'bad') || '—'}</div></div>
<div class="col-12"><div class="cardx"><h6>Recommended keywords</h6>${chips(d.keywords) || '—'}</div></div>
<div class="col-md-6"><div class="cardx"><h6>Experience comparison</h6><p class="mb-0">${esc(d.experience_comparison)}</p></div></div>
<div class="col-md-6"><div class="cardx"><h6>Education comparison</h6><p class="mb-0">${esc(d.education_comparison)}</p></div></div></div>
<div class="row g-3">${list('Relevant Experience', d.relevant_experience, 'ok')}${list('Missing Qualifications', d.missing_qualifications, 'bad')}${list('Improvement Suggestions', d.suggestions)}</div>`,

  improve: (d) => `<div class="row g-3 mb-3"><div class="col-md-6"><div class="cardx"><h6>Original</h6><div class="cmp" id="orig">${esc(d.original) || '<span class="text-muted">—</span>'}</div></div>
<div class="col-md-6"><div class="cardx" style="border:2px solid #a5b4fc"><div class="d-flex justify-content-between"><h6>Improved</h6><button class="btn btn-sm btn-grad" data-copy="#impr"><i class="bi bi-clipboard"></i> Copy</button></div><div class="cmp" id="impr">${esc(d.improved)}</div></div></div></div>
<div class="row g-3"><div class="col-md-6"><div class="cardx"><h6>Strong action verbs</h6>${chips(d.action_verbs) || '—'}</div></div><div class="col-md-6"><div class="cardx"><h6>Recommended skills</h6>${chips(d.recommended_skills) || '—'}</div></div>
${list('What changed', d.changes)}${d.notes ? `<div class="col-md-6"><div class="cardx"><h6>Notes</h6><p class="mb-0">${esc(d.notes)}</p></div></div>` : ''}</div>`
};

// Chart Generators
const C = {
  analysis: d => {
    const el = $('#ch');
    if (!el) return;
    new Chart(el, {
      type: 'radar',
      data: {
        labels: Object.keys(d.scores || {}).map(cap),
        datasets: [{
          data: Object.values(d.scores || {}),
          backgroundColor: '#4f46e533',
          borderColor: '#4f46e5',
          pointBackgroundColor: '#8b5cf6'
        }]
      },
      options: {
        scales: { r: { min: 0, max: 100 } },
        plugins: { legend: { display: false } }
      }
    });
  },
  match: d => {
    const el = $('#ch');
    if (!el) return;
    new Chart(el, {
      type: 'bar',
      data: {
        labels: ['Required', 'Matching', 'Missing'],
        datasets: [{
          data: [
            (d.required_skills || []).length,
            (d.matching_skills || []).length,
            (d.missing_skills || []).length
          ],
          backgroundColor: ['#6366f1', '#22c55e', '#ef4444'],
          borderRadius: 8
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
      }
    });
  },
  dashboard: (chartData) => {
    const el = $('#prog');
    if (!el || !chartData) return;
    const an = chartData.an || [];
    const ats = chartData.ats || [];
    const n = Math.max(an.length, ats.length, 1);
    new Chart(el, {
      type: 'line',
      data: {
        labels: Array.from({ length: n }, (_, i) => 'Run ' + (i + 1)),
        datasets: [
          {
            label: 'Resume score',
            data: an,
            borderColor: '#4f46e5',
            backgroundColor: '#4f46e522',
            fill: true,
            tension: 0.35
          },
          {
            label: 'ATS score',
            data: ats,
            borderColor: '#8b5cf6',
            tension: 0.35
          }
        ]
      },
      options: {
        scales: { y: { min: 0, max: 100 } }
      }
    });
  }
};

// Clipboard copy delegation
document.addEventListener('click', e => {
  const b = e.target.closest('[data-copy]');
  if (!b) return;
  const target = $(b.dataset.copy);
  if (!target) return;
  navigator.clipboard.writeText(target.innerText).then(() => {
    const o = b.innerHTML;
    b.innerHTML = '<i class="bi bi-check2"></i> Copied';
    setTimeout(() => { b.innerHTML = o; }, 1500);
  });
});

// Sidebar active link + mobile menu toggle + logout
document.addEventListener('DOMContentLoaded', () => {
  // Mobile drawer toggle
  $('#menu')?.addEventListener('click', () => {
    $('.side')?.classList.toggle('open');
  });

  // Logout button
  $('#logout-btn')?.addEventListener('click', async (e) => {
    e.preventDefault();
    await API.auth.logout();
    window.location.href = 'login.html';
  });

  // Highlight active sidebar link
  const currentPath = window.location.pathname.split('/').pop() || 'index.html';
  const urlParams = new URLSearchParams(window.location.search);
  const currentKind = urlParams.get('kind');

  $$('.side a').forEach(a => {
    const href = a.getAttribute('href');
    if (!href) return;
    if (currentKind && href.includes(`kind=${currentKind}`)) {
      a.classList.add('active');
    } else if (!currentKind && href === currentPath) {
      a.classList.add('active');
    }
  });
});

// App Router / Page Initializers
window.App = {
  showResult(kind, result) {
    const container = $('#result');
    if (!container) return;
    container.innerHTML = R[kind](result.data, result.score);
    setTimeout(() => {
      $$('.bar i').forEach(b => {
        b.style.width = (b.dataset.w || 0) + '%';
      });
    }, 60);
    if (C[kind]) C[kind](result.data);
    container.scrollIntoView({ behavior: 'smooth' });
  },

  initLanding() {
    if (API.isAuthenticated()) {
      const cta = $('#hero-cta');
      if (cta) {
        cta.textContent = 'Go to Dashboard';
        cta.setAttribute('href', 'dashboard.html');
      }
      const navLinks = $('#nav-auth-links');
      if (navLinks) {
        navLinks.innerHTML = `
          <a class="btn btn-outline-light rounded-pill" href="dashboard.html">Dashboard</a>
          <button class="btn btn-light rounded-pill fw-semibold" id="nav-logout">Logout</button>
        `;
        $('#nav-logout')?.addEventListener('click', async () => {
          await API.auth.logout();
          window.location.reload();
        });
      }
    }
  },

  initLogin() {
    if (API.isAuthenticated()) {
      window.location.href = 'dashboard.html';
      return;
    }
    const form = $('#login-form');
    const alertBox = $('#alert-box');
    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      alertBox.innerHTML = '';
      const btn = $('button[type=submit]', form);
      btn.disabled = true;
      btn.textContent = 'Logging in...';

      try {
        const username = $('#username').value.trim();
        const password = $('#password').value;
        await API.auth.login({ username, password });
        window.location.href = 'dashboard.html';
      } catch (err) {
        alertBox.innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`;
        btn.disabled = false;
        btn.textContent = 'Login';
      }
    });
  },

  initRegister() {
    if (API.isAuthenticated()) {
      window.location.href = 'dashboard.html';
      return;
    }
    const form = $('#register-form');
    const alertBox = $('#alert-box');
    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      alertBox.innerHTML = '';

      const p1 = $('#password').value;
      const p2 = $('#password_confirm').value;
      if (p1 !== p2) {
        alertBox.innerHTML = '<div class="alert alert-danger">Passwords do not match.</div>';
        return;
      }

      const btn = $('button[type=submit]', form);
      btn.disabled = true;
      btn.textContent = 'Creating account...';

      try {
        const payload = {
          username: $('#username').value.trim(),
          email: $('#email').value.trim(),
          password: p1,
          first_name: $('#first_name')?.value.trim() || '',
          last_name: $('#last_name')?.value.trim() || ''
        };
        await API.auth.register(payload);
        window.location.href = 'dashboard.html';
      } catch (err) {
        alertBox.innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`;
        btn.disabled = false;
        btn.textContent = 'Sign up';
      }
    });
  },

  async initDashboard() {
    if (!API.isAuthenticated()) {
      window.location.href = 'login.html';
      return;
    }

    try {
      const data = await API.dashboard.getData();
      const user = data.user || API.getUser() || {};
      const displayName = user.first_name || user.username || 'User';
      $('#welcome-name').textContent = displayName;

      $('#stat-resumes').textContent = data.n_resumes ?? 0;
      $('#stat-analyses').textContent = data.n_analyses ?? 0;
      $('#stat-last-an').textContent = data.last_an !== null ? data.last_an : '—';
      $('#stat-last-ats').textContent = data.last_ats !== null ? data.last_ats : '—';

      // Matches list
      const matchesContainer = $('#recent-matches');
      if (matchesContainer) {
        if (data.matches && data.matches.length > 0) {
          matchesContainer.innerHTML = data.matches.map(m => `
            <div class="d-flex justify-content-between border-bottom py-2">
              <span>${esc(m.job_title)} <small class="text-muted">· ${esc(m.resume_title)}</small></span>
              <b>${m.score}%</b>
            </div>
          `).join('');
        } else {
          matchesContainer.innerHTML = '<p class="text-muted">No job matches yet.</p>';
        }
      }

      // Recent resumes list
      const resumesContainer = $('#recent-resumes');
      if (resumesContainer) {
        if (data.recent_resumes && data.recent_resumes.length > 0) {
          resumesContainer.innerHTML = data.recent_resumes.map(r => `
            <div class="py-1">
              📄 ${esc(r.title)} <small class="text-muted">${formatDate(r.created)}</small>
            </div>
          `).join('');
        } else {
          resumesContainer.innerHTML = '<p class="text-muted">Nothing uploaded yet.</p>';
        }
      }

      // Progress Chart
      if (data.chart) {
        C.dashboard(data.chart);
      }
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    }
  },

  async initUpload() {
    if (!API.isAuthenticated()) {
      window.location.href = 'login.html';
      return;
    }

    const drop = $('#drop');
    const inp = $('#fileinp');
    const form = $('#upform');
    const alertBox = $('#alert-box');
    const resumeGrid = $('#resume-grid');
    const maxMb = 5;

    const pick = () => {
      const fl = inp.files[0];
      if (!fl) return;
      const ok = /\.(pdf|docx)$/i.test(fl.name);
      if (!ok || fl.size > maxMb * 1048576) {
        alert(!ok ? 'Only PDF and DOCX files are allowed.' : `File is larger than ${maxMb} MB.`);
        inp.value = '';
        return;
      }
      $('#dname').textContent = `${fl.name} (${(fl.size / 1024).toFixed(0)} KB)`;
    };

    if (inp) inp.addEventListener('change', pick);
    if (drop) {
      ['dragover', 'dragenter'].forEach(ev => drop.addEventListener(ev, e => {
        e.preventDefault();
        drop.classList.add('over');
      }));
      ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => {
        e.preventDefault();
        drop.classList.remove('over');
      }));
      drop.addEventListener('drop', e => {
        inp.files = e.dataTransfer.files;
        pick();
      });
    }

    const loadResumes = async () => {
      try {
        const resumes = await API.resumes.list();
        if (!resumeGrid) return;
        if (!resumes || resumes.length === 0) {
          resumeGrid.innerHTML = '<p class="text-muted">No resumes yet.</p>';
          return;
        }

        resumeGrid.innerHTML = resumes.map(r => `
          <div class="col-md-6 col-xl-4" id="resume-card-${r.id}">
            <div class="cardx">
              <h6><i class="bi bi-file-earmark-text text-grad"></i> ${esc(r.title)}</h6>
              <small class="text-muted">${formatDate(r.created)} · ${r.word_count || 0} words</small>
              <div class="d-flex flex-wrap gap-1 mt-3">
                <button class="btn btn-sm btn-outline-primary preview-btn" data-id="${r.id}">Preview</button>
                <a class="btn btn-sm btn-outline-secondary" target="_blank" href="${API.resumes.getFileUrl(r.id)}">Open file</a>
                <a class="btn btn-sm btn-outline-success" href="tool.html?kind=analysis&resume=${r.id}">Analyze</a>
                <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${r.id}">Delete</button>
              </div>
            </div>
          </div>
        `).join('');
      } catch (err) {
        console.error('Failed to load resumes:', err);
      }
    };

    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      alertBox.innerHTML = '';
      const file = inp?.files[0];
      if (!file) {
        alertBox.innerHTML = '<div class="alert alert-danger">Please choose a file.</div>';
        return;
      }

      const btn = $('button[type=submit]', form);
      btn.disabled = true;
      btn.textContent = 'Uploading & extracting...';

      try {
        const fd = new FormData();
        fd.append('file', file);
        const titleVal = $('#resume-title')?.value.trim();
        if (titleVal) fd.append('title', titleVal);

        const res = await API.resumes.upload(fd);
        alertBox.innerHTML = `<div class="alert alert-success">${esc(res.message || 'Resume uploaded successfully.')}</div>`;
        form.reset();
        $('#dname').textContent = 'Drag & drop your resume here or click to browse';
        await loadResumes();
      } catch (err) {
        alertBox.innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`;
      } finally {
        btn.disabled = false;
        btn.textContent = 'Upload & extract text';
      }
    });

    // Preview and Delete listeners
    document.addEventListener('click', async (e) => {
      const prevBtn = e.target.closest('.preview-btn');
      if (prevBtn) {
        const id = prevBtn.dataset.id;
        try {
          const res = await API.resumes.getText(id);
          $('#pt').textContent = res.title;
          $('#pb').textContent = res.text;
          new bootstrap.Modal('#pm').show();
        } catch (err) {
          alert(err.message);
        }
        return;
      }

      const delBtn = e.target.closest('.delete-btn');
      if (delBtn) {
        const id = delBtn.dataset.id;
        if (!confirm('Delete this resume and its analyses?')) return;
        try {
          await API.resumes.delete(id);
          const card = $(`#resume-card-${id}`);
          if (card) card.remove();
          if ($$('#resume-grid .cardx').length === 0) {
            resumeGrid.innerHTML = '<p class="text-muted">No resumes yet.</p>';
          }
        } catch (err) {
          alert('Delete failed: ' + err.message);
        }
      }
    });

    await loadResumes();
  },

  async initTool() {
    if (!API.isAuthenticated()) {
      window.location.href = 'login.html';
      return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const kind = urlParams.get('kind') || 'analysis';
    const selResumeId = urlParams.get('resume') || '';
    const loadAnalysisId = urlParams.get('r');

    const meta = TOOL_INFO[kind] || TOOL_INFO.analysis;
    $('#tool-title').textContent = meta.title;
    $('#tool-desc').textContent = meta.desc;

    // Show kind-specific input sections
    if (kind === 'match') {
      $('#match-fields')?.classList.remove('d-none');
    } else if (kind === 'improve') {
      $('#improve-fields')?.classList.remove('d-none');
    }

    const resumeSelect = $('#resume-select');
    const noResumesAlert = $('#no-resumes-alert');
    const form = $('#toolform');
    const alertBox = $('#alert');

    try {
      const resumes = await API.resumes.list();
      if (!resumes || resumes.length === 0) {
        noResumesAlert?.classList.remove('d-none');
        form?.classList.add('d-none');
        return;
      }

      resumeSelect.innerHTML = resumes.map(r => `
        <option value="${r.id}" ${String(r.id) === selResumeId ? 'selected' : ''}>${esc(r.title)}</option>
      `).join('');
    } catch (err) {
      alertBox.innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`;
    }

    // Load past analysis if requested
    if (loadAnalysisId) {
      try {
        const res = await API.analysis.get(kind, loadAnalysisId);
        if (res && res.data) {
          if (res.resume_id && resumeSelect) {
            resumeSelect.value = res.resume_id;
          }
          App.showResult(kind, res);
        }
      } catch (err) {
        alertBox.innerHTML = `<div class="alert alert-warning">Could not load previous analysis: ${esc(err.message)}</div>`;
      }
    }

    // Form submission
    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      alertBox.innerHTML = '';
      const submitBtn = $('button[type=submit]', form);
      const spinner = $('.spin');

      submitBtn.disabled = true;
      spinner?.classList.remove('d-none');

      try {
        const payload = {
          resume_id: resumeSelect.value
        };

        if (kind === 'match') {
          payload.job_title = $('#job_title')?.value.trim() || '';
          payload.job_description = $('#job_description')?.value.trim() || '';
          if (payload.job_description.length < 50) {
            throw new Error('Please paste a fuller job description (at least 50 characters).');
          }
        } else if (kind === 'improve') {
          payload.section = $('#section-select')?.value || 'Professional Summary';
          payload.original = $('#original-text')?.value.trim() || '';
          payload.facts = $('#facts-text')?.value.trim() || '';
        }

        const result = await API.analysis.run(kind, payload);
        App.showResult(kind, result);
      } catch (err) {
        alertBox.innerHTML = `<div class="alert alert-danger">${esc(err.message)} Click "Run Analysis" to retry.</div>`;
      } finally {
        submitBtn.disabled = false;
        spinner?.classList.add('d-none');
      }
    });
  },

  async initHistory() {
    if (!API.isAuthenticated()) {
      window.location.href = 'login.html';
      return;
    }

    const tbody = $('#history-tbody');
    try {
      const rows = await API.analysis.history();
      if (!tbody) return;
      if (!rows || rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center py-4">No analyses yet.</td></tr>';
        return;
      }

      tbody.innerHTML = rows.map(r => `
        <tr>
          <td><b>${esc(r.label)}</b></td>
          <td>${esc(r.resume_title)}</td>
          <td>${r.score !== null ? `<span class="chip">${r.score}</span>` : '—'}</td>
          <td>${formatDate(r.created)}</td>
          <td>
            <a class="btn btn-sm btn-outline-primary" href="tool.html?kind=${r.kind}&r=${r.id}">View</a>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-danger">${esc(err.message)}</td></tr>`;
      }
    }
  },

  async initProfile() {
    if (!API.isAuthenticated()) {
      window.location.href = 'login.html';
      return;
    }

    const form = $('#profile-form');
    const alertBox = $('#alert-box');

    try {
      const data = await API.auth.me();
      const u = data.user || {};
      const p = u.profile || {};

      $('#profile-username').textContent = u.username || '';
      $('#first_name').value = u.first_name || '';
      $('#last_name').value = u.last_name || '';
      $('#email').value = u.email || '';
      $('#phone').value = p.phone || '';
      $('#target_role').value = p.target_role || '';
      $('#bio').value = p.bio || '';
    } catch (err) {
      alertBox.innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`;
    }

    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      alertBox.innerHTML = '';
      const btn = $('button[type=submit]', form);
      btn.disabled = true;
      btn.textContent = 'Saving...';

      try {
        const payload = {
          first_name: $('#first_name').value.trim(),
          last_name: $('#last_name').value.trim(),
          email: $('#email').value.trim(),
          phone: $('#phone').value.trim(),
          target_role: $('#target_role').value.trim(),
          bio: $('#bio').value.trim()
        };
        const res = await API.auth.updateProfile(payload);
        alertBox.innerHTML = `<div class="alert alert-success">${esc(res.message || 'Profile updated successfully.')}</div>`;
      } catch (err) {
        alertBox.innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`;
      } finally {
        btn.disabled = false;
        btn.textContent = 'Save changes';
      }
    });
  }
};
