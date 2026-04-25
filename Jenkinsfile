pipeline {
    agent any

    stages {

        stage('Clone') {
            steps {
                git branch: 'main',
                url: 'www.github.com/KrutiSoumya/MedInsight'
            }
        }

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
                docker stop medinsight-container
                docker rm medinsight-container
                docker run -d -p 8501:8501 --name medinsight-container medinsight
                '''
            }
        }
    }
}