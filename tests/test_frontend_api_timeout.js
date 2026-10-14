const http = require('http');

async function testTimeout() {
  const payload = JSON.stringify({
    geometry: {
      type: "Polygon",
      coordinates: [[[73.7, 18.5], [73.71, 18.5], [73.71, 18.51], [73.7, 18.51], [73.7, 18.5]]]
    },
    // We pass an invalid mode that could hang if unhandled, or just rely on the 45s timeout.
    mode: "uehi" 
  });

  const options = {
    hostname: 'localhost',
    port: 3000,
    path: '/api/study-area',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload)
    }
  };

  const startTime = Date.now();
  
  const req = http.request(options, (res) => {
    let data = '';
    res.on('data', (chunk) => {
      data += chunk;
    });
    res.on('end', () => {
      const elapsed = Date.now() - startTime;
      console.log(`Response received in ${elapsed}ms with status ${res.statusCode}`);
      // As long as it responds before 50 seconds, we consider it a pass (the timeout is 45s)
      if (elapsed > 50000) {
        console.error("FAIL: Request hung indefinitely.");
        process.exit(1);
      }
      
      console.log("PASS: Request did not hang indefinitely.");
      process.exit(0);
    });
  });

  req.on('error', (e) => {
    console.error(`Problem with request: ${e.message}`);
    process.exit(1);
  });

  req.write(payload);
  req.end();
}

testTimeout();
