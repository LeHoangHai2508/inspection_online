function addFieldRow() {
  const tbody = document.querySelector('#fields-table tbody');
  const row = document.createElement('tr');
  row.innerHTML = `
    <td>
      <select name="side[]" class="select-sm">
        <option value="side1">side1</option>
        <option value="side2">side2</option>
      </select>
    </td>
    <td><input name="field_name[]" value="" class="input-sm" /></td>
    <td><input name="expected_value[]" value="" class="input-sm" /></td>
    <td>
      <select name="compare_type[]" class="select-sm">
        <option value="exact">exact</option>
        <option value="regex">regex</option>
        <option value="fuzzy">fuzzy</option>
        <option value="symbol_match">symbol_match</option>
      </select>
    </td>
    <td>
      <select name="priority[]" class="select-sm">
        <option value="critical">critical</option>
        <option value="major" selected>major</option>
        <option value="minor">minor</option>
      </select>
    </td>
    <td><input type="checkbox" name="required[]" checked /></td>
    <td><button type="button" class="btn btn-sm btn-danger" onclick="removeRow(this)">✕</button></td>
  `;
  tbody.appendChild(row);
}

function removeRow(btn) {
  btn.closest('tr').remove();
}

// Intercept form submit → send as JSON to PUT /templates/:id/fields
document.getElementById('field-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const action = form.action;
  const templateId = action.split('/templates/')[1].split('/')[0];

  const rows = form.querySelectorAll('#fields-table tbody tr');
  const fields = Array.from(rows).map(row => ({
    side: row.querySelector('[name="side[]"]')?.value || 'side1',
    field_name: row.querySelector('[name="field_name[]"]').value,
    expected_value: row.querySelector('[name="expected_value[]"]').value,
    compare_type: row.querySelector('[name="compare_type[]"]').value,
    priority: row.querySelector('[name="priority[]"]').value,
    required: row.querySelector('[name="required[]"]')?.checked ?? true,
    field_type: 'text',
  }));

  try {
    await postJSON(`/api/templates/${templateId}/fields`, { fields, review_notes: 'reviewed via web UI' });
    alert('Fields saved.');
    location.reload();
  } catch (err) {
    alert('Error: ' + err.message);
  }
});

// Helper function for form submission
async function postForm(url, formDataObj) {
  const body = new URLSearchParams(formDataObj);
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body,
  });

  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.detail || 'Request failed');
  }
  return data;
}

// Handle approve form
document.getElementById('approve-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const approvedBy = form.querySelector('[name="approved_by"]').value;

  try {
    const data = await postForm(form.action, { approved_by: approvedBy });
    alert('Approve thành công. Status: ' + (data.status || 'APPROVED'));
    location.reload();
  } catch (err) {
    alert('Approve lỗi: ' + err.message);
  }
});

// Handle reject form
document.getElementById('reject-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;

  try {
    const resp = await fetch(form.action, { method: 'POST' });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      throw new Error(data.detail || 'Reject failed');
    }
    alert('Reject xong.');
    location.reload();
  } catch (err) {
    alert('Reject lỗi: ' + err.message);
  }
});
