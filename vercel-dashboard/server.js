const express = require('express');
const path = require('path');

const app = express();
const port = 8000;

// Serve static files from the current directory
app.use(express.static(__dirname));

app.get("/api/tenders", (req, res) => {
  const jsonPath = "../output/new_tenders.json";
  delete require.cache[require.resolve(jsonPath)];
  const data = require(jsonPath);
  res.json(data);
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
