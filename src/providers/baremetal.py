from src import config
from src.connection import run_command


def deploy_baremetal(conn):
    """Deploy directly to server without Docker/K8s"""
    with conn.cd(config.GIT_SUBDIR):
        deploy_script_check = conn.run("test -f deploy.sh", hide=True, warn=True)
        if deploy_script_check.ok:
            print("======= Running deploy.sh =======")
            conn.run("chmod +x deploy.sh", warn=True)
            result = run_command(
                conn,
                "./deploy.sh; EXIT_CODE=$?; if [ $EXIT_CODE -ne 0 ]; then echo 'Command failed with exit code:' $EXIT_CODE; exit $EXIT_CODE; fi",
            )
            if "Command failed with exit code:" in result.stdout:
                for line in result.stdout.split("\n"):
                    if "Command failed with exit code:" in line:
                        exit_code = line.split("exit code:")[-1].strip()
                        raise ValueError(f"deploy.sh failed with exit code: {exit_code}")
        else:
            makefile_check = conn.run("test -f Makefile", hide=True, warn=True)
            if makefile_check.ok:
                print(f"======= Running make target: {config.ENVIRONMENT} =======")
                result = run_command(
                    conn,
                    f"make {config.ENVIRONMENT}; EXIT_CODE=$?; if [ $EXIT_CODE -ne 0 ]; then echo 'Command failed with exit code:' $EXIT_CODE; exit $EXIT_CODE; fi",
                )
                if "Command failed with exit code:" in result.stdout:
                    for line in result.stdout.split("\n"):
                        if "Command failed with exit code:" in line:
                            exit_code = line.split("exit code:")[-1].strip()
                            raise ValueError(
                                f"make {config.ENVIRONMENT} failed with exit code: {exit_code}"
                            )
            else:
                raise ValueError(
                    "No deploy_command specified and no deploy.sh or Makefile found. Please specify deploy_command input."
                )
    print("======= Baremetal deployment completed =======")
