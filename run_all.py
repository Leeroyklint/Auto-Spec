"""
Lance backend (uvicorn) et frontend (streamlit) dans le même terminal.
Utilise `python -m` pour être indépendant du PATH Windows.
"""
import subprocess, sys, pathlib, os, time, signal

ROOT = pathlib.Path(__file__).parent.resolve()
ENV = os.environ.copy()


def spawn(module: str, args: list, cwd: pathlib.Path):
    cmd = [sys.executable, "-m", module] + args
    return subprocess.Popen(cmd, cwd=cwd, env=ENV)


def main():
    try:
        print("⏳ Backend (uvicorn)…")
        back = spawn("uvicorn", ["backend.app.main:app", "--reload", "--port", "8000"], ROOT)
        time.sleep(2)

        print("⏳ Frontend (streamlit)…")
        front = spawn("streamlit", ["run", "frontend/app.py", "--server.port", "8501"], ROOT)

        print(
            "\n✅ Prêt !\n"
            "  • Backend : http://127.0.0.1:8000/docs\n"
            "  • Frontend : http://127.0.0.1:8501\n"
            "Ctrl-C pour arrêter."
        )

        while True:
            time.sleep(3)

    except KeyboardInterrupt:
        print("\n🛑 Arrêt…")
        for p in (front, back):
            if p and p.poll() is None:
                p.send_signal(signal.SIGINT)
        for p in (front, back):
            if p:
                p.wait()


if __name__ == "__main__":
    main()
