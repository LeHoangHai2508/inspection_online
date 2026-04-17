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

async function inspectSide2() {
  const scanJobId = document.getElementById('scan_job_id').value.trim();
  const templateId = document.getElementById('template_id').value.trim();
  const cam1 = document.getElementById('cam1_file').files[0];
  const cam2 = document.getElementById('cam2_file').files[0];

  if (!cam1 || !cam2) { alert('Cần upload cả cam1 và cam2.'); return; }

  const fd = new FormData();
  fd.append('scan_job_id', scanJobId);
  fd.append('template_id', templateId);
  fd.append('cam1_file', cam1);
  fd.append('cam2_file', cam2);

  document.getElementById('btn-inspect').disabled = true;
  try {
    const result = await postForm('/api/inspection/side2', fd);
    renderSide2Result(result);
  } catch (err) {
    alert('Error: ' + err.message);
  } finally {
    document.getElementById('btn-inspect').disabled = false;
  }
}

async function inspectSide2Live() {
  const scanJobId = document.getElementById('scan_job_id').value.trim();
  const templateId = document.getElementById('template_id').value.trim();

  const fd = new FormData();
  fd.append('scan_job_id', scanJobId);
  fd.append('template_id', templateId);

  document.getElementById('btn-live').disabled = true;
  try {
    const result = await postForm('/api/inspection/side2/live', fd);
    renderSide2Result(result);
  } catch (err) {
    alert('Error: ' + err.message);
  } finally {
    document.getElementById('btn-live').disabled = false;
  }
}

function renderSide2Result(result) {
  const panel = document.getElementById('side2-result');
  panel.classList.remove('hidden');
  panel.innerHTML = renderSideResult(result, 'Side 2');

  // Redirect to overall result page
  const scanJobId = document.getElementById('scan_job_id').value.trim();
  setTimeout(() => {
    window.location.href = `/result/${scanJobId}`;
  }, 1500);
}
