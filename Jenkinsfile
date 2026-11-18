// ---------------------------------------------------------------------------
// Jenkins version of our CI pipeline (for comparison with GitHub Actions).
// Our team uses GitHub Actions (.github/workflows/ci.yml) as the main pipeline.
// This file lets a Jenkins server run the same steps: install, lint, test.
// ---------------------------------------------------------------------------
pipeline {
    agent any

    triggers {
        // Check GitHub for new commits every 5 minutes
        // (or use a GitHub webhook for instant triggering)
        pollSCM('H/5 * * * *')
    }

    stages {
        stage('Install') {
            steps {
                sh 'python3 -m venv venv'
                sh './venv/bin/pip install -r requirements.txt flake8'
            }
        }
        stage('Lint') {
            steps {
                sh './venv/bin/flake8 .'
            }
        }
        stage('Test') {
            steps {
                sh './venv/bin/python -m unittest -v'
            }
        }
    }

    post {
        success { echo 'All tests passed. Safe to merge.' }
        failure { echo 'Tests failed. Do not merge this change.' }
    }
}
