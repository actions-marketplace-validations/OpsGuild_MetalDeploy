from src import config
from src.connection import run_command
from src.providers.docker import docker_login

def install_kubectl(conn):
    """Install kubectl if not already installed"""
    kubectl_check = conn.run("which kubectl", warn=True, hide=True)
    if kubectl_check.stdout.strip():
        print("======= kubectl already installed =======")
        return
    print("======= Installing kubectl =======")
    version_result = conn.run("curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt", hide=True)
    latest_version = version_result.stdout.strip()
    conn.run(f"curl -LO https://storage.googleapis.com/kubernetes-release/release/{latest_version}/bin/linux/amd64/kubectl")
    conn.run("chmod +x ./kubectl")
    run_command(conn, "mv ./kubectl /usr/local/bin/kubectl", force_sudo=True)
    print("======= kubectl installed =======")

def install_helm(conn):
    """Install helm if not already installed"""
    helm_check = conn.run("which helm", warn=True, hide=True)
    if helm_check.stdout.strip():
        print("======= helm already installed =======")
        return
    print("======= Installing helm =======")
    if config.REMOTE_PASSWORD:
        escaped_pwd = config.REMOTE_PASSWORD.replace("'", "'\"'\"'")
        conn.run(f"cat > /tmp/helm-askpass.sh << 'HELMASKPASS_EOF'\n#!/bin/sh\nprintf '%s\\n' '{escaped_pwd}'\nHELMASKPASS_EOF", warn=False)
        conn.run("chmod +x /tmp/helm-askpass.sh", warn=False)
        conn.run("curl -s https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 > /tmp/get-helm-3.sh", warn=False)
        conn.run("sed -i 's/sudo /sudo -A /g' /tmp/get-helm-3.sh", warn=False)
        conn.run("chmod +x /tmp/get-helm-3.sh", warn=False)
        conn.run("SUDO_ASKPASS=/tmp/helm-askpass.sh bash /tmp/get-helm-3.sh", pty=False, warn=False)
    else:
        conn.run("curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash", warn=False)
    print("======= helm installed =======")

def install_k3s(conn):
    """Install k3s if not already installed"""
    result = conn.run("which k3s", warn=True, hide=True)
    if result.stdout.strip():
        print("======= k3s already installed =======")
        return
    print("======= Installing k3s =======")
    conn.run('curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable=traefik" sh -', pty=True)
    run_command(conn, "systemctl enable k3s", force_sudo=True)
    run_command(conn, "systemctl start k3s", force_sudo=True)
    conn.run("echo 'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml' >> ~/.bashrc")
    print("======= k3s installed =======")

def deploy_k8s(conn):
    """Deploy using Kubernetes"""
    with conn.cd(config.GIT_SUBDIR):
        docker_login(conn, registry_type=config.REGISTRY_TYPE)
        manifest_path = config.K8S_MANIFEST_PATH
        if not manifest_path:
            for path in ["k8s", "manifests", "kubernetes"]:
                if conn.run(f"test -d {path}", hide=True, warn=True).ok:
                    manifest_path = path
                    break
            if not manifest_path:
                for file in ["k8s.yaml", "k8s.yml", "deployment.yaml", "deployment.yml"]:
                    if conn.run(f"test -f {file}", hide=True, warn=True).ok:
                        manifest_path = file
                        break
        if not manifest_path: raise ValueError("No k8s_manifest_path specified and no k8s manifests found.")
        print(f"======= Deploying to Kubernetes using: {manifest_path} =======")
        kubeconfig_cmd = "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml"
        conn.run(f"{kubeconfig_cmd} && kubectl create namespace {config.K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -")
        if conn.run(f"test -d {manifest_path}", warn=True, hide=True).ok:
            conn.run(f"{kubeconfig_cmd} && kubectl apply -f {manifest_path}/ -n {config.K8S_NAMESPACE}")
        else:
            conn.run(f"{kubeconfig_cmd} && kubectl apply -f {manifest_path} -n {config.K8S_NAMESPACE}")
    print("======= Kubernetes deployment completed =======")
