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
