pipeline {
    agent any

    stages {

        stage('Build') {
            steps {
                bat 'docker build -t medinsight .'
            }
        }

        stage('Test') {
            steps {
                bat 'docker run --rm medinsight pytest'
            }
        }

        stage('Deploy') {
            steps {
                bat '''
                docker stop medinsight-container || exit 0
                docker rm medinsight-container || exit 0
                docker run -d -p 8501:8501 --name medinsight-container medinsight
                '''
            }
        }
    }
}