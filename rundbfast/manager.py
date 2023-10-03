import os
import shutil
import subprocess
import time
from rich.console import Console

console = Console()

class CommandRunner:
    @staticmethod
    def run_command(command):
        try:
            return subprocess.run(command, shell=True, check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as e:
            console.print(f"Error executing '{command}':", e.stderr, style="bold red")
            raise

class DockerManager:
    def __init__(self):
        self.runner = CommandRunner()

    def is_installed(self):
        return bool(shutil.which('docker'))

    def install(self):
        self.runner.run_command("sudo apt update")
        self.runner.run_command("sudo apt install -y docker.io")
        self.runner.run_command("sudo systemctl start docker")
        self.runner.run_command("sudo systemctl enable docker")

    def pull_image(self, image):
        self.runner.run_command(f"docker pull {image}")

    def container_exists(self, container_name):
        existing_containers = self.runner.run_command(f"docker ps -a -q -f name={container_name}")
        return bool(existing_containers)

    def remove_container(self, container_name):
        self.runner.run_command(f"docker stop {container_name}")
        self.runner.run_command(f"docker rm {container_name}")

class PostgreSQLManager:
    def __init__(self, container_name):
        self.container_name = container_name
        self.runner = CommandRunner()

    def start_container(self, password):
        self.runner.run_command(f"docker run --name {self.container_name} -e POSTGRES_PASSWORD={password} -p 5432:5432 -d postgres:latest")

    def is_ready(self):
        try:
            output = self.runner.run_command(f"docker exec {self.container_name} pg_isready")
            return "accepting connections" in output
        except:
            return False

    def wait_for_ready(self, timeout=60):
        start_time = time.time()
        while True:
            if self.is_ready():
                return True
            elif time.time() - start_time > timeout:
                raise TimeoutError("Timed out waiting for PostgreSQL to be ready")
            time.sleep(2)

    def database_exists(self, db_name):
        result = self.runner.run_command(f"docker exec {self.container_name} psql -U postgres -tAc \"SELECT 1 FROM pg_database WHERE datname='{db_name}'\"")
        return bool(result)

    def setup_database(self):
        if not self.database_exists('synthextra'):
            self.runner.run_command(f"docker exec {self.container_name} psql -U postgres -c 'CREATE DATABASE synthextra;'")
        self.runner.run_command(f"docker exec {self.container_name} psql -U postgres -d synthextra -c 'CREATE EXTENSION IF NOT EXISTS cube;'")

    def container_exists(self):
        existing_containers = self.runner.run_command(f"docker ps -a -q -f name={self.container_name}")
        return bool(existing_containers)

    def remove_container(self):
        if self.container_exists():
            print(f"Container with name {self.container_name} already exists. Stopping and removing...")
            self.runner.run_command(f"docker stop {self.container_name}")
            self.runner.run_command(f"docker rm {self.container_name}")
            time.sleep(5)  # Give Docker a few seconds to free up the name

    def ensure_data_persistence(self, password):
        self.remove_container()
        print("Setting up Docker volume for data persistence...")
        self.runner.run_command(f"docker run --name {self.container_name} -e POSTGRES_PASSWORD={password} -p 5432:5432 -v postgres_data:/var/lib/postgresql/data -d postgres:latest")

class PgAdminManager:
    def __init__(self, container_name="pgadmin4"):
        self.container_name = container_name
        self.runner = CommandRunner()

    def start_container(self, email, password):
        self.runner.run_command(f"docker run --name {self.container_name} -p 80:80 \
            -e 'PGADMIN_DEFAULT_EMAIL={email}' \
            -e 'PGADMIN_DEFAULT_PASSWORD={password}' \
            -d dpage/pgadmin4")

    def container_exists(self):
        existing_containers = self.runner.run_command(f"docker ps -a -q -f name={self.container_name}")
        return bool(existing_containers)

    def remove_container(self):
        if self.container_exists():
            print(f"Container with name {self.container_name} already exists. Stopping and removing...")
            self.runner.run_command(f"docker stop {self.container_name}")
            self.runner.run_command(f"docker rm {self.container_name}")
            time.sleep(5)  # Give Docker a few seconds to free up the name
