const apiToken = localStorage.getItem('apiToken') || '';

async function fetchStatus() {
  const res = await fetch('/status', { headers: { 'X-API-Token': apiToken } });
  const data = await res.json();
  const tbody = document.querySelector('#status-table tbody');
  tbody.innerHTML = '';
  const addRow = (type, status, count) => {
    const tr = document.createElement('tr');
    tr.className = statusClass(status);
    tr.innerHTML = `<td>${type}</td><td>${status}</td><td>${count}</td>`;
    tbody.appendChild(tr);
  };
  for (const [status, count] of Object.entries(data.account_health)) {
    addRow('Account', status, count);
  }
  for (const [status, count] of Object.entries(data.proxy_health)) {
    addRow('Proxy', status, count);
  }
}

function statusClass(status) {
  status = status.toLowerCase();
  if (status.includes('healthy') || status.includes('good')) return 'green';
  if (status.includes('unknown')) return 'yellow';
  return 'red';
}

async function fetchLogs() {
  const res = await fetch('/log', { headers: { 'X-API-Token': apiToken } });
  const data = await res.json();
  const container = document.getElementById('logs');
  container.innerHTML = data.map(r => `<div>${r.site || ''}: ${r.review_text || r.review}</div>`).join('');
}

document.getElementById('submit-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    site: document.getElementById('site').value,
    template: document.getElementById('template').value,
    review_text: document.getElementById('review-text').value,
    proxy_id: document.getElementById('proxy').value || null,
    account_id: document.getElementById('account').value || null,
  };
  await fetch('/submit_review', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Token': apiToken,
    },
    body: JSON.stringify(payload),
  });
  document.getElementById('submit-form').reset();
  fetchLogs();
});

fetchStatus();
fetchLogs();
setInterval(fetchLogs, 5000);

const getStartedBtn = document.getElementById('get-started-btn');
if (getStartedBtn) {
  getStartedBtn.addEventListener('click', () => {
    document.getElementById('submit-section').scrollIntoView({ behavior: 'smooth' });
  });
}
