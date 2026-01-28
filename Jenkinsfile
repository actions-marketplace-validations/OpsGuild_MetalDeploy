pipeline {
    agent {
        docker {
            image "ghcr.io/opsguild/metal-deploy:latest"
            // Mount docker socket if performing docker/k8s deployments
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }

    parameters {
        string(name: 'GIT_URL', defaultValue: '', description: 'Git repository URL to clone and deploy')
        choice(name: 'GIT_AUTH_METHOD', choices: ['token', 'ssh', 'none'], description: 'Git authentication method')
        password(name: 'GIT_TOKEN', defaultValue: '', description: 'GitHub token (if using token auth)')
        string(name: 'GIT_USER', defaultValue: '', description: 'GitHub username (if using token auth)')
        string(name: 'ENVIRONMENT', defaultValue: 'dev', description: 'Deployment environment (dev, staging, prod)')
        string(name: 'REMOTE_HOST', defaultValue: '', description: 'SSH remote host IP or domain')
        string(name: 'REMOTE_USER', defaultValue: 'root', description: 'SSH remote user')
        password(name: 'SSH_KEY', defaultValue: '', description: 'SSH private key (base64 encoded or raw)')
        choice(name: 'DEPLOYMENT_TYPE', choices: ['baremetal', 'docker', 'k8s'], description: 'Deployment type')
    }

    environment {
        // Map Jenkins parameters to environment variables used by the script
        GIT_URL = "${params.GIT_URL}"
        GIT_AUTH_METHOD = "${params.GIT_AUTH_METHOD}"
        GIT_TOKEN = "${params.GIT_TOKEN}"
        GIT_USER = "${params.GIT_USER}"
        ENVIRONMENT = "${params.ENVIRONMENT}"
        REMOTE_HOST = "${params.REMOTE_HOST}"
        REMOTE_USER = "${params.REMOTE_USER}"
        SSH_KEY = "${params.SSH_KEY}"
        DEPLOYMENT_TYPE = "${params.DEPLOYMENT_TYPE}"

        // Environment File Generation examples:
        // Variables starting with ENV_ will automatically be converted to .env files
        ENV_FILES_GENERATE = "true"
        // ENV_APP_DATABASE_URL = "postgres://user:pass@host:5432/db" // Map from credentials
    }

    stages {
        stage('Deploy') {
            steps {
                script {
                    // Automatically map ALL Jenkins parameters to environment variables
                    // This means any parameter you define (e.g. ENV_APP_DB)
                    // is automatically available to the script without manual mapping.
                    def paramEnv = params.collect { k, v -> "${k}=${v}" }

                    withEnv(paramEnv) {
                        echo "Starting deployment to ${env.REMOTE_HOST} (${env.ENVIRONMENT})..."
                        sh "python main.py"
                    }
                }
            }
        }
    }

    post {
        success {
            echo "Deployment successful!"
        }
        failure {
            echo "Deployment failed!"
        }
    }
}
