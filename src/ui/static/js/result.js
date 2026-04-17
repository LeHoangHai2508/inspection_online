// Shared helpers used across all pages

function statusBadge(status) {
  const cls = { OK: 'ok', NG: 'ng', UNCERTAIN: 'uncertain' }[status] || 'pending';
  return `<span class="badge badge-${cls}">${status || '—'}</span>`;
}

function severityBadge(sev) {
  return `<span class="badge badge-${sev || 'minor'}">${sev || '—'}</span>`;
}

function renderErrors(errors) {
  if (!errors || errors.length === 0) return '<p class="text-ok">Không có lỗi.</p>';
  const rows = errors.map(e => `
    <tr class="row-${e.severity}">
      <td>${e.field_name || '—'}</td>
      <td>${e.error_type}</td>
      <td>${severityBadge(e.severity)}</td>
      <td>${e.expected_value || '—'}</td>
      <td>${e.actual_value || '—'}</td>
    </tr>`).join('');
  return `<table class="data-table">
    <thead><tr><th>Field</th><th>Error</th><th>Severity</th><th>Expected</th><th>Actual</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function renderSideResult(result, title) {
  if (!result) return '';
  return `
    <div class="side-panel">
      <h2>${title} — ${statusBadge(result.status)}</h2>
      <p class="proc-time">${result.processing_time_ms || 0} ms</p>
      ${renderErrors(result.errors)}
    </div>`;
}

async function postForm(url, formData) {
  const resp = await fetch(url, { method: 'POST', body: formData });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || resp.statusText);
  }
  return resp.json();
}

async function postJSON(url, data) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || resp.statusText);
  }
  return resp.json();
}
