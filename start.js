const { exec } = require("child_process");
const openModule = require("open"); // import module

// Use default function
const open = openModule.default || openModule;

// Start server with nodemon
const nodemon = exec("npx nodemon server.js");

nodemon.stdout.on("data", data => process.stdout.write(data));
nodemon.stderr.on("data", data => process.stderr.write(data));

// Wait 2 seconds and open browser
setTimeout(() => {
  open("http://localhost:3000");
}, 2000);
