const state = { evidenceCount: 0, result: null, processingTimer: null };
const $ = (selector) => document.querySelector(selector);
const el = (tag, className) => { const node = document.createElement(tag); if (className) node.className = className; return node; };

function toast(message) {
  const node = $('#toast');
  node.textContent = message;
  node.classList.add('show');
  setTimeout(() => node.classList.remove('show'), 2600);
}

function addEvidence(item = {}) {
  if (state.evidenceCount >= 10) return toast('The evidence bed holds up to ten items.');
  state.evidenceCount += 1;
  const row = el('div', 'evidence-row');
  row.innerHTML = `
    <span class="evidence-id">E${state.evidenceCount}</span>
    <input class="evidence-title" maxlength="100" aria-label="Evidence title" placeholder="Source label" value="${escapeAttribute(item.title || '')}">
    <input class="evidence-content" maxlength="1800" aria-label="Evidence content" placeholder="A fact, observation, quote, or measured result" value="${escapeAttribute(item.content || '')}">
    <button class="remove-evidence" type="button" aria-label="Remove evidence">×</button>`;
  row.querySelector('.remove-evidence').addEventListener('click', () => { row.remove(); renumberEvidence(); });
  $('#evidenceList').appendChild(row);
}

function renumberEvidence() {
  const rows = [...document.querySelectorAll('.evidence-row')];
  rows.forEach((row, index) => row.querySelector('.evidence-id').textContent = `E${index + 1}`);
  state.evidenceCount = rows.length;
}

function escapeAttribute(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;');
}

function requestFromForm() {
  const evidence = [...document.querySelectorAll('.evidence-row')].map((row, index) => ({
    id: `E${index + 1}`,
    title: row.querySelector('.evidence-title').value.trim(),
    content: row.querySelector('.evidence-content').value.trim(),
  })).filter((item) => item.title && item.content);
  return {
    question: $('#question').value.trim(),
    context: $('#context').value.trim(),
    constraints: $('#constraints').value.split('\n').map(v => v.trim()).filter(Boolean),
    evidence,
  };
}

async function loadSample() {
  const response = await fetch('/api/sample');
  const sample = await response.json();
  $('#question').value = sample.question;
  $('#context').value = sample.context;
  $('#constraints').value = sample.constraints.join('\n');
  $('#evidenceList').innerHTML = '';
  state.evidenceCount = 0;
  sample.evidence.forEach(addEvidence);
  $('#question').focus();
  toast('Example planted. Edit anything you like.');
}

function beginProcessing(showcase = false) {
  const overlay = $('#processing');
  overlay.classList.remove('hidden');
  const labels = showcase
    ? ['Loading the prepared decision', 'Replaying role-separated passes', 'Revealing the evidence trail', 'Opening the ledger']
    : ['Role-separated seats are taking root', 'The breaker is testing assumptions', 'The grounder is tracing evidence', 'The arbiter is preserving dissent'];
  const steps = [...document.querySelectorAll('.processing-steps span')];
  let index = 0;
  $('#processingTitle').textContent = labels[0];
  steps.forEach((step, i) => step.classList.toggle('active', i === 0));
  state.processingTimer = setInterval(() => {
    index = Math.min(index + 1, labels.length - 1);
    $('#processingTitle').textContent = labels[index];
    steps.forEach((step, i) => step.classList.toggle('active', i <= index));
  }, showcase ? 380 : 2300);
}

function endProcessing() {
  clearInterval(state.processingTimer);
  $('#processing').classList.add('hidden');
}

async function run(endpoint, showcase = false) {
  if (!showcase && !$('#question').value.trim()) return toast('Plant a decision first.');
  beginProcessing(showcase);
  const options = { method: 'POST', headers: { 'Content-Type': 'application/json' } };
  if (!showcase) options.body = JSON.stringify(requestFromForm());
  try {
    const response = await fetch(endpoint, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'The deliberation could not complete.');
    if (showcase) await new Promise(resolve => setTimeout(resolve, 1250));
    renderResult(data);
    await refreshLedger();
  } catch (error) {
    toast(error.message);
  } finally {
    endProcessing();
  }
}

function renderResult(result) {
  state.result = result;
  $('#decisionOutput').textContent = result.decision;
  $('#survivingCore').textContent = result.surviving_core;
  $('#tensionOutput').textContent = result.unresolved_tension;
  $('#testOutput').textContent = result.next_test;
  $('#decisionId').textContent = result.decision_id;
  const modeLabels = { live: 'Live deliberation', showcase: 'Showcase dataset', reused: 'Verified receipt reuse' };
  $('#resultMode').textContent = modeLabels[result.mode] || result.mode;
  $('#resultModel').textContent = result.model;
  const coverage = Math.round(result.claim_survival_rate * 100);
  $('#coverageValue').textContent = `${coverage}%`;
  $('#coverageRing').style.setProperty('--coverage', `${coverage}%`);
  $('#receiptHash').textContent = `SHA-256 ${result.receipt_hash.slice(0, 18)}…`;
  const governor = result.governor || {};
  $('#governorMode').textContent = governor.mode || 'BUILD';
  $('#governorInput').textContent = Number(governor.input_tokens || 0).toLocaleString();
  $('#governorOutput').textContent = Number(governor.output_tokens || 0).toLocaleString();
  $('#governorSaved').textContent = Number(governor.saved_tokens || 0).toLocaleString();
  const contextEstimate = Number(governor.estimated_context_tokens_avoided || 0);
  $('#governorNote').textContent = (governor.note || 'No prior receipt was relevant.')
    + (contextEstimate ? ` Estimated context reduction: ${contextEstimate.toLocaleString()} tokens.` : '');

  const icons = { builder: '↗', breaker: '⚡', grounder: '⌁' };
  $('#seatGrid').replaceChildren(...result.seats.map((seat) => {
    const card = el('article', `seat-card ${seat.seat}`);
    const claims = seat.claims.map(claim => `
      <div class="seat-claim">${escapeHtml(claim.statement)}
        <div class="evidence-chips">${claim.evidence_ids.map(id => `<span>${id}</span>`).join('') || '<span>Inference</span>'}</div>
      </div>`).join('');
    card.innerHTML = `
      <div class="seat-top"><span class="seat-name">${seat.seat}</span><span class="seat-icon">${icons[seat.seat]}</span></div>
      <div class="seat-body"><p class="seat-thesis">${escapeHtml(seat.thesis)}</p>${claims}</div>
      <div class="seat-question"><strong>Question left open</strong>${escapeHtml(seat.question_for_others)}</div>`;
    return card;
  }));

  $('#claimBoard').replaceChildren(...result.claims.map((claim) => {
    const row = el('article', `claim-row ${claim.status}`);
    const evidence = claim.evidence_ids.length ? claim.evidence_ids.join(' · ') : 'No supplied evidence';
    row.innerHTML = `
      <div class="claim-id">${claim.id}</div>
      <div class="claim-copy"><p>${escapeHtml(claim.statement)}</p><small>${escapeHtml(claim.challenge)} · ${evidence}</small></div>
      <div class="claim-status"><i></i>${claim.status}</div>`;
    return row;
  }));

  $('#results').classList.remove('hidden');
  setTimeout(() => $('#results').scrollIntoView({ behavior: 'smooth', block: 'start' }), 80);
}

function escapeHtml(value) {
  const node = document.createElement('div');
  node.textContent = value;
  return node.innerHTML;
}

async function refreshHealth() {
  try {
    const response = await fetch('/api/health');
    const health = await response.json();
    const status = $('#apiStatus');
    status.classList.toggle('live', health.live_ready);
    status.lastChild.textContent = health.live_ready ? ` GPT‑5.6 live` : ' Showcase ready';
  } catch { $('#apiStatus').lastChild.textContent = ' Server offline'; }
}

async function refreshLedger() {
  const response = await fetch('/api/ledger');
  const data = await response.json();
  $('#ledgerCount').textContent = data.records.length;
  $('#ledgerVerification').textContent = data.verification.valid
    ? `✓ Chain verified · ${data.verification.records} records · head ${data.verification.head.slice(0, 12)}…`
    : `! Ledger verification failed: ${data.verification.error}`;
  $('#ledgerList').replaceChildren(...data.records.map(record => {
    const item = el('article', 'ledger-item');
    const payload = record.payload;
    const isDecision = record.kind === 'decision';
    const isReuse = record.kind === 'reuse';
    const title = isDecision ? payload.result.decision : isReuse ? `Receipt reused for ${payload.decision_id}` : `Correction to ${payload.decision_id}`;
    const detail = isDecision ? payload.request.question : isReuse ? `${payload.saved_tokens.toLocaleString()} tokens avoided; source ${payload.source_receipt.slice(0, 12)}…` : payload.note;
    item.innerHTML = `
      <div class="ledger-item-header"><span>${record.kind} · #${record.index}</span><span>${new Date(record.timestamp).toLocaleDateString()}</span></div>
      <h3>${escapeHtml(title)}</h3><p>${escapeHtml(detail)}</p>
      <div class="ledger-hash">${record.record_hash}</div>`;
    return item;
  }));
}

function setDrawer(open) {
  $('#ledgerDrawer').classList.toggle('open', open);
  $('#scrim').classList.toggle('open', open);
  $('#ledgerDrawer').setAttribute('aria-hidden', String(!open));
}

async function appendCorrection(event) {
  event.preventDefault();
  if (!state.result) return;
  const note = $('#correctionNote').value.trim();
  if (note.length < 5) return;
  const response = await fetch(`/api/decisions/${state.result.decision_id}/corrections`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ note }),
  });
  if (!response.ok) return toast('Correction could not be appended.');
  $('#correctionDialog').close();
  $('#correctionNote').value = '';
  await refreshLedger();
  toast('Correction appended. The original remains visible.');
}

$('#addEvidence').addEventListener('click', () => addEvidence());
$('#sampleButton').addEventListener('click', loadSample);
$('#showcaseButton').addEventListener('click', () => run('/api/showcase', true));
$('#decisionForm').addEventListener('submit', (event) => { event.preventDefault(); run('/api/deliberate'); });
$('#ledgerButton').addEventListener('click', async () => { await refreshLedger(); setDrawer(true); });
$('#closeDrawer').addEventListener('click', () => setDrawer(false));
$('#scrim').addEventListener('click', () => setDrawer(false));
$('#correctButton').addEventListener('click', () => $('#correctionDialog').showModal());
$('#correctionForm').addEventListener('submit', appendCorrection);
document.addEventListener('keydown', event => { if (event.key === 'Escape') setDrawer(false); });

addEvidence();
refreshHealth();
refreshLedger();
