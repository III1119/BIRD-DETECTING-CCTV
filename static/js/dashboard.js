const API_ENDPOINT = '/api/detections';
const POLL_INTERVAL = 5000;

const countEl = document.getElementById('detection-count');
const tableBody = document.querySelector('#detection-table tbody');
const lastUpdatedEl = document.getElementById('last-updated');

function formatTimestamp(timestamp) {
  if (!timestamp) {
    return 'N/A';
  }
  const date = new Date(timestamp * 1000);
  return date.toLocaleString();
}

function renderDetections(detections) {
  tableBody.innerHTML = '';
  if (!detections.length) {
    const row = document.createElement('tr');
    row.innerHTML = '<td colspan="2" class="empty">감지된 항목이 없습니다.</td>';
    tableBody.appendChild(row);
    return;
  }

  detections.forEach((det) => {
    const row = document.createElement('tr');
    const labelCell = document.createElement('td');
    labelCell.textContent = det.label;
    const confidenceCell = document.createElement('td');
    confidenceCell.textContent = det.confidence.toFixed(2);
    row.append(labelCell, confidenceCell);
    tableBody.appendChild(row);
  });
}

async function refreshSummary() {
  try {
    const response = await fetch(API_ENDPOINT, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error('Failed to fetch detection summary');
    }
    const summary = await response.json();
    countEl.textContent = summary.count;
    lastUpdatedEl.textContent = formatTimestamp(summary.last_updated);
    renderDetections(summary.detections || []);
  } catch (error) {
    console.error(error);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  refreshSummary();
  setInterval(refreshSummary, POLL_INTERVAL);
});
