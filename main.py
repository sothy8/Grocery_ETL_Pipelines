from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from socket import create_connection
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SPARK_HOME = "/Users/vandethsothy/Apache-Spark/spark-3.5.8-bin-hadoop3"
FRONTEND_DIR = BASE_DIR / "frontend"
SPARK_KAFKA_PACKAGE = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8"


def run_command(command: list[str], env: dict[str, str] | None = None) -> None:
    print(f"\n>> Running: {' '.join(command)}")
    try:
        subprocess.run(command, check=True, env=env)
    except KeyboardInterrupt:
        raise


def start_source_api(env: dict[str, str]) -> subprocess.Popen:
    print("\n>> Starting source API...")
    return subprocess.Popen([env["PYTHON"], "-m", "src.ingest.source_api"], env=env)


def start_backend(env: dict[str, str], host: str, port: int, reload: bool) -> subprocess.Popen:
    print("\n>> Starting FastAPI backend...")
    command = [
        env["PYTHON"],
        "-m",
        "uvicorn",
        "src.app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        command.append("--reload")
    return subprocess.Popen(command, env=env)


def start_frontend() -> subprocess.Popen:
    print("\n>> Starting Next.js frontend...")
    return subprocess.Popen(["npm", "run", "dev"], cwd=FRONTEND_DIR)


def spark_submit_with_kafka(spark_submit: Path, script: str) -> list[str]:
    return [
        str(spark_submit),
        "--packages",
        SPARK_KAFKA_PACKAGE,
        script,
    ]


def stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def build_env(python_executable: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE_DIR)
    env["PYTHON"] = python_executable
    return env


def resolve_python(venv_path: Path | None) -> str:
    if venv_path:
        return str(venv_path / "bin" / "python")
    return sys.executable


def parse_bootstrap_server(bootstrap_servers: str) -> tuple[str, int]:
    server = bootstrap_servers.split(",")[0].strip()
    host, _, port_text = server.partition(":")
    return host or "localhost", int(port_text or "9092")


def wait_for_kafka(bootstrap_servers: str, timeout_seconds: int, interval_seconds: int) -> None:
    host, port = parse_bootstrap_server(bootstrap_servers)
    deadline = time.time() + timeout_seconds
    print(f"\n>> Waiting for Kafka at {host}:{port} ...")

    while time.time() < deadline:
        try:
            with create_connection((host, port), timeout=2):
                print(f">> Kafka is ready at {host}:{port}")
                return
        except OSError:
            time.sleep(interval_seconds)

    raise TimeoutError(f"Kafka was not ready at {host}:{port} after {timeout_seconds}s")


def wait_for_source_api(api_url: str, timeout_seconds: int, interval_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    probe_url = f"{api_url.rstrip('/')}/sales?limit=1&offset=0"
    print(f"\n>> Waiting for source API at {api_url} ...")

    while time.time() < deadline:
        try:
            response = requests.get(probe_url, timeout=3)
            if response.ok:
                print(f">> Source API is ready at {api_url}")
                return
        except requests.RequestException:
            pass
        time.sleep(interval_seconds)

    raise TimeoutError(f"Source API was not ready at {api_url} after {timeout_seconds}s")


def start_server_stack(env: dict[str, str], host: str, port: int, reload: bool) -> list[tuple[str, subprocess.Popen]]:
    procs: list[tuple[str, subprocess.Popen]] = []
    procs.append(("backend", start_backend(env, host, port, reload)))
    if FRONTEND_DIR.exists():
        procs.append(("frontend", start_frontend()))
    else:
        print(f"Frontend directory not found: {FRONTEND_DIR}")

    print("\nSource API: http://localhost:8001")
    print(f"Backend: http://{host}:{port}")
    print("Frontend: http://localhost:3000")
    return procs


def assert_processes_alive(procs: list[tuple[str, subprocess.Popen]]) -> None:
    for name, proc in list(procs):
        exit_code = proc.poll()
        if exit_code is not None:
            raise SystemExit(f"{name} exited with code {exit_code}")


def run_servers(env: dict[str, str], host: str, port: int, reload: bool) -> None:
    procs: list[tuple[str, subprocess.Popen]] = []
    try:
        procs = start_server_stack(env, host, port, reload)

        while True:
            for name, proc in list(procs):
                exit_code = proc.poll()
                if exit_code is not None:
                    raise SystemExit(f"{name} exited with code {exit_code}")
            signal.pause()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
    finally:
        for _, proc in procs:
            stop_process(proc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the grocery ETL pipeline end-to-end.")
    parser.add_argument("--spark-home", default=DEFAULT_SPARK_HOME, help="Path to SPARK_HOME")
    parser.add_argument("--venv", default=".venv", help="Path to venv directory")
    parser.add_argument("--skip-source-api", action="store_true", help="Skip starting source API")
    parser.add_argument("--realtime", action="store_true", help="Run pipeline in realtime streaming mode")
    parser.add_argument("--servers", action="store_true", default=True, help="Start backend and frontend after pipeline")
    parser.add_argument("--no-servers", action="store_false", dest="servers", help="Do not start backend and frontend after pipeline")
    parser.add_argument("--servers-only", action="store_true", help="Only start backend and frontend")
    parser.add_argument("--backend-host", default="127.0.0.1")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--no-reload", action="store_true", help="Disable backend auto-reload")
    args = parser.parse_args()

    venv_path = Path(args.venv)
    python_executable = resolve_python(venv_path if venv_path.exists() else None)
    env = build_env(python_executable)

    spark_home = args.spark_home
    spark_submit = Path(spark_home) / "bin" / "spark-submit"
    if not spark_submit.exists():
        raise FileNotFoundError(f"spark-submit not found at {spark_submit}")

    bootstrap_servers = env.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_wait_timeout = int(env.get("KAFKA_WAIT_TIMEOUT", "120"))
    kafka_wait_interval = int(env.get("KAFKA_WAIT_INTERVAL", "2"))
    source_api_url = env.get("SOURCE_API_URL", "http://localhost:8001")
    source_api_wait_timeout = int(env.get("SOURCE_API_WAIT_TIMEOUT", "120"))
    source_api_wait_interval = int(env.get("SOURCE_API_WAIT_INTERVAL", "2"))

    if args.servers_only:
        run_servers(env, args.backend_host, args.backend_port, not args.no_reload)
        return

    source_proc: subprocess.Popen | None = None
    producer_proc: subprocess.Popen | None = None
    spark_proc: subprocess.Popen | None = None
    silver_gold_proc: subprocess.Popen | None = None
    server_procs: list[tuple[str, subprocess.Popen]] = []
    try:
        if not args.skip_source_api:
            source_proc = start_source_api(env)
            wait_for_source_api(source_api_url, source_api_wait_timeout, source_api_wait_interval)
            print(f"\nSource API: {source_api_url}")

        wait_for_kafka(bootstrap_servers, kafka_wait_timeout, kafka_wait_interval)

        if args.servers:
            server_procs = start_server_stack(env, args.backend_host, args.backend_port, not args.no_reload)

        if args.realtime:
            # Start continuous Kafka producer (RUN_CONTINUOUS=1)
            realtime_env = env.copy()
            realtime_env["RUN_CONTINUOUS"] = "1"
            realtime_env.setdefault("PRODUCER_POLL_INTERVAL", "5")
            print("\n>> Starting continuous kafka producer (realtime mode)...")
            producer_proc = subprocess.Popen([python_executable, "-m", "src.ingest.kafka_producer"], env=realtime_env)

            # Start Spark structured streaming job
            print("\n>> Starting Spark structured streaming job: stream_to_bronze.py")
            spark_proc = subprocess.Popen(spark_submit_with_kafka(spark_submit, "src/etl/stream_to_bronze.py"), env=env)

            # Wait for stream_to_bronze to write at least one batch before starting silver/gold
            print("\n>> Waiting 30s for bronze stream to initialize before starting silver/gold scorer...")
            time.sleep(30)

            print("\n>> Starting Spark streaming scorer: stream_silver_gold.py")
            silver_gold_proc = subprocess.Popen(
                spark_submit_with_kafka(spark_submit, "src/etl/stream_silver_gold.py"), env=env
            )

            print("Realtime pipeline running. Press Ctrl+C to stop.")

            try:
                while True:
                    if producer_proc and producer_proc.poll() is not None:
                        raise SystemExit("producer exited")
                    if spark_proc and spark_proc.poll() is not None:
                        raise SystemExit("spark job exited")
                    if silver_gold_proc and silver_gold_proc.poll() is not None:
                        raise SystemExit("silver_gold job exited")
                    assert_processes_alive(server_procs)
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

        else:
            # Batch pipeline (existing behavior)
            try:
                run_command([python_executable, "-m", "src.ingest.kafka_producer"], env=env)
                run_command([str(spark_submit), "src/etl/batch_to_bronze.py"], env=env)
                run_command([str(spark_submit), "src/etl/silver_gold.py"], env=env)
                run_command([python_executable, "-m", "src.training.train_model"], env=env)
                run_command([python_executable, "-m", "src.warehouse.load_gold_to_postgres"], env=env)
                print("\nAll pipeline steps completed.")
            except KeyboardInterrupt:
                print("\nPipeline interrupted.")

            if args.servers and server_procs:
                print("\nServers are still running. Press Ctrl+C to stop the backend and frontend.")
                try:
                    while True:
                        assert_processes_alive(server_procs)
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
    finally:
        if producer_proc:
            stop_process(producer_proc)
        if spark_proc:
            stop_process(spark_proc)
        if silver_gold_proc:
            stop_process(silver_gold_proc)
        if source_proc:
            stop_process(source_proc)
        for _, proc in server_procs:
            stop_process(proc)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
