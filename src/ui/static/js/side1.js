// Preview images on file select
['cam1_file', 'cam2_file'].forEach(id => {
  document.getElementById(id)?.addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    const previewId = id === 'cam1_file' ? 'preview-cam1' : 'preview-cam2';
    const img = document.getElementById(previewId);
    img.src = URL.createObjectURL(file);
    img.style.display = 'block';
  });
});

async function inspectSide1() {
  const scanJobId = document.getElementById('scan_job_id').value.trim();
  const templateId = document.getElementById('template_id').value.trim();
  const cam1 = document.getElementById('cam1_file').files[0];
  const cam2 = document.getElementById('cam2_file').files[0];

  if (!scanJobId || !templateId || !cam1 || !cam2) {
    alert('Điền đủ Scan Job ID, Template ID và 2 ảnh.');
    return;
  }

  const fd = new FormData();
  fd.append('scan_job_id', scanJobId);
  fd.append('template_id', templateId);
  fd.append('cam1_file', cam1);
  fd.append('cam2_file', cam2);

  document.getElementById('btn-inspect').disabled = true;
  try {
    const result = await postForm('/api/inspection/side1', fd);
    sessionStorage.setItem('side1_result', JSON.stringify(result));
    sessionStorage.setItem('scan_job_id', scanJobId);
    sessionStorage.setItem('template_id', templateId);
    renderSide1Result(result);
  } catch (err) {
    alert('Error: ' + err.message);
  } finally {
    document.getElementById('btn-inspect').disabled = false;
  }
}

async function inspectSide1Live() {
  const scanJobId = document.getElementById('scan_job_id').value.trim();
  const templateId = document.getElementById('template_id').value.trim();
  if (!scanJobId || !templateId) { alert('Điền Scan Job ID và Template ID.'); return; }

  const fd = new FormData();
  fd.append('scan_job_id', scanJobId);
  fd.append('template_id', templateId);

  document.getElementById('btn-live').disabled = true;
  try {
    const result = await postForm('/api/inspection/side1/live', fd);
    sessionStorage.setItem('side1_result', JSON.stringify(result));
    sessionStorage.setItem('scan_job_id', scanJobId);
    sessionStorage.setItem('template_id', templateId);
    renderSide1Result(result);
  } catch (err) {
    alert('Error: ' + err.message);
  } finally {
    document.getElementById('btn-live').disabled = false;
  }
}

function renderSide1Result(result) {
  const panel = document.getElementById('side1-result');
  panel.classList.remove('hidden');
  panel.innerHTML = renderSideResult(result, 'Side 1');

  // Redirect to confirm page after short delay
  setTimeout(() => {
    const scanJobId = sessionStorage.getItem('scan_job_id');
    window.location.href = `/inspect/${scanJobId}/confirm-side2`;
  }, 1500);
}
