import express from "express";
import path from "path";
import { spawn, ChildProcess } from "child_process";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = 3000;
const PYTHON_API_PORT = 8000;
const PYTHON_API_URL = `http://127.0.0.1:${PYTHON_API_PORT}`;

// Middleware to parse JSON and text
app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true, limit: "10mb" }));

// Launch Python FastAPI + APScheduler backend process
let pythonProcess: ChildProcess | null = null;

function startPythonBackend() {
  console.log("Starting Python FastAPI & APScheduler backend...");
  pythonProcess = spawn("python3", ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(PYTHON_API_PORT)], {
    stdio: "inherit",
    env: { ...process.env, PYTHONUNBUFFERED: "1" }
  });

  pythonProcess.on("error", (err) => {
    console.error("Failed to start Python backend:", err);
  });

  pythonProcess.on("exit", (code, signal) => {
    console.log(`Python backend process exited with code ${code}, signal ${signal}`);
  });
}

startPythonBackend();

// Proxy /api/* requests to FastAPI
app.use("/api", async (req, res) => {
  const targetUrl = `${PYTHON_API_URL}/api${req.url}`;
  try {
    const headers: Record<string, string> = {};
    for (const [key, value] of Object.entries(req.headers)) {
      if (typeof value === "string" && key.toLowerCase() !== "host") {
        headers[key] = value;
      }
    }

    const fetchOptions: RequestInit = {
      method: req.method,
      headers: {
        ...headers,
        "content-type": req.headers["content-type"] || "application/json"
      }
    };

    if (["POST", "PUT", "PATCH"].includes(req.method.toUpperCase())) {
      fetchOptions.body = JSON.stringify(req.body);
    }

    const response = await fetch(targetUrl, fetchOptions);
    const contentType = response.headers.get("content-type") || "application/json";

    res.status(response.status);
    res.setHeader("content-type", contentType);

    if (contentType.includes("application/json")) {
      const data = await response.json();
      res.json(data);
    } else {
      const text = await response.text();
      res.send(text);
    }
  } catch (err: any) {
    console.error(`Proxy error to ${targetUrl}:`, err.message);
    res.status(502).json({
      error: "FastAPI Backend unavailable or starting up",
      message: err.message
    });
  }
});

async function startServer() {
  // Vite middleware in dev mode
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  const server = app.listen(PORT, "0.0.0.0", () => {
    console.log(`AI Workforce Allocation Agent running on http://0.0.0.0:${PORT}`);
  });

  // Graceful shutdown
  const shutdown = () => {
    console.log("Shutting down servers...");
    if (pythonProcess) {
      pythonProcess.kill("SIGTERM");
    }
    server.close(() => {
      process.exit(0);
    });
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

startServer();
