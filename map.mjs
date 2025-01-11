import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { WebSocketServer } from 'ws';

// For ESM usage
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 4000;

// Middleware to parse JSON requests
app.use(express.json());

app.use(express.static(path.join(__dirname, 'public')));

app.get('/map', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Endpoint to receive GeoCLIP or user coordinates
app.post('/geoclip', (req, res) => {
  const { lat, lon, probability, image, detections } = req.body;

  if (!lat || !lon) {
    res.status(400).send({ error: 'Missing required lat/lon fields.' });
    return;
  }

  console.log(`Received: Latitude=${lat}, Longitude=${lon}, Probability=${probability}, Image=${image}, Detections=${detections}`);

  // Send data to all connected WebSocket clients
  wss.clients.forEach((client) => {
    if (client.readyState === 1) { // WebSocket.OPEN
      client.send(JSON.stringify({ lat, lon, probability, image, detections }));
    }
  });

  res.status(200).send('Data received and broadcast.');
});


// Start the server
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}/map`);
});

// WebSocket server for real-time updates
const wss = new WebSocketServer({ port: 4001 });
wss.on('connection', (ws) => {
  console.log('WebSocket connection established.');
});

