// Initialize the map centered on Vienna
const map = L.map('map').setView([48.2082, 16.3738], 13);

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '© OpenStreetMap',
}).addTo(map);

// Establish WebSocket connection
const ws = new WebSocket('ws://localhost:4001');

// Handle incoming messages from the WebSocket
ws.onmessage = (event) => {
  try {
    const data = JSON.parse(event.data);
    const { lat, lon, probability, image, detections } = data;

    // Ensure detections is an array or handle it gracefully
    const detectionsList = Array.isArray(detections) ? detections.join(', ') : 'None';

    // Build the popup content
    const popupContent = `
      <strong>Marker at (${lat}, ${lon})</strong><br>
      Probability: ${probability || 'N/A'}<br>
      Detections: ${detectionsList}<br>
      ${image ? `<img src="${image}" alt="Detection Image" style="max-width:100px;"/>` : ''}
    `;

    // Add the marker with the popup to the map
    L.marker([lat, lon])
      .addTo(map)
      .bindPopup(popupContent)
      .openPopup();
  } catch (error) {
    console.error('Error processing WebSocket message:', error);
  }
};

// Handle WebSocket connection errors
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

