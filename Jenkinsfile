pipeline {
    agent {
        docker { 
            image "ghcr.io/opsguild/metaldeploy:latest"
            registryUrl "https://ghcr.io"
            registryCredentialsId "github-registry-auth"
            // Reset entrypoint to allow running shell commands
            args '--entrypoint="" -v /var/run/docker.sock:/var/run/docker.sock'
        }
    }

    environment {
        GIT_AUTH_METHOD = 'token'
        USE_SUDO = 'true'
        DEPLOYMENT_TYPE= 'baremetal'
        ENV_FILES_GENERATE = 'true'
        ENV_FILES_STRUCTURE = 'auto'
        ENV_FILES_CREATE_ROOT = 'false'
        ENV_FILES_FORMAT = 'auto'
    }

    stages {
        // --- STAGING ---
        stage('Deploy Staging') {
            when { branch 'staging' }
            steps {
                withCredentials([
                    // Staging Secrets (Use unique IDs!)
                    string(credentialsId: 'git-token',         variable: 'GIT_TOKEN'),
                    string(credentialsId: 'staging-remote-pass', variable: 'REMOTE_PASSWORD'),
                    string(credentialsId: 'staging-remote-host', variable: 'REMOTE_HOST'),
                    
                    file(credentialsId: 'staging-app-env',      variable: 'ENV_APP'),
                    file(credentialsId: 'staging-atlas-env',    variable: 'ENV_ATLAS'),
                    file(credentialsId: 'staging-database-env', variable: 'ENV_DATABASE'),
                    file(credentialsId: 'staging-minio-env',    variable: 'ENV_MINIO'),
                    file(credentialsId: 'staging-redis-env',    variable: 'ENV_REDIS')
                ]) {
                   script {
                       def cmd = 'export env=staging && make up && make migrate'
                       withEnv(["ENVIRONMENT=staging", "DEPLOY_COMMAND=${cmd}"]) {
                           // Use absolute path to the tool inside the container
                           sh "python /app/main.py"
                       }
                   }
                }
            }
        }

        // --- PRODUCTION ---
        stage('Deploy Production') {
            when { branch 'main' }
            steps {
                withCredentials([
                    // Production Secrets
                    string(credentialsId: 'git-token',      variable: 'GIT_TOKEN'),
                    string(credentialsId: 'prod-remote-pass', variable: 'REMOTE_PASSWORD'),
                    string(credentialsId: 'prod-remote-host', variable: 'REMOTE_HOST'),

                    file(credentialsId: 'prod-app-env',      variable: 'ENV_APP'),
                    file(credentialsId: 'prod-atlas-env',    variable: 'ENV_ATLAS'),
                    file(credentialsId: 'prod-database-env', variable: 'ENV_DATABASE'),
                    file(credentialsId: 'prod-minio-env',    variable: 'ENV_MINIO'),
                    file(credentialsId: 'prod-redis-env',    variable: 'ENV_REDIS')
                ]) {
                   script {
                       def cmd = 'export env=prod && make up && make migrate'
                       withEnv(["ENVIRONMENT=prod", "DEPLOY_COMMAND=${cmd}"]) {
                           sh "python /app/main.py"
                       }
                   }
                }
            }
        }
    }
}
