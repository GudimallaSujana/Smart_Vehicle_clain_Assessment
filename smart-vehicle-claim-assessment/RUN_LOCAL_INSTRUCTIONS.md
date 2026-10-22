# Run locally on Windows

`localhost` works only when the backend and frontend are running on **your own PC**.

## Easiest method

1. Install Python 3.10+ from <https://www.python.org/downloads/>.
   - Tick **Add Python to PATH** during installation.
2. Install Node.js LTS from <https://nodejs.org/>.
3. Open the `smart-vehicle-claim-assessment` folder.
4. Double-click:

```text
RUN_LOCAL_WINDOWS.bat
```

It opens two terminal windows:

- Backend API: <http://localhost:8000/docs>
- Frontend website: <http://localhost:5173/>

Keep both terminal windows open.

## Manual method

Open two separate terminals inside the project folder.

### Terminal 1: backend

```bat
cd smart-vehicle-claim-assessment
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Then open:

```text
http://localhost:8000/docs
```

### Terminal 2: frontend

```bat
cd smart-vehicle-claim-assessment\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Then open:

```text
http://localhost:5173/
```

## If you still get `localhost refused to connect`

Check these:

1. The two terminal windows must still be open.
2. Backend terminal must show something like:

```text
Uvicorn running on http://127.0.0.1:8000
```

3. Frontend terminal must show something like:

```text
Local: http://localhost:5173/
```

4. If a port is busy, stop old servers or change ports.
5. If Python or npm is not recognized, reinstall Python/Node.js and add them to PATH.

If it still fails, send a screenshot or copy-paste the error text from the two terminal windows.
