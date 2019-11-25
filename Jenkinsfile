pipeline {
  agent any
  stages {
    stage('Build and Test') {
      steps {
        sh 'docker-compose build --no-cache'
      }
    }
    stage('Deploy Integration'){
      when {
        expression { BRANCH_NAME == 'integration' }
      }
      environment {
        BOT_CONFIG_FILE = credentials('')
      }
      steps {
        sh 'docker-compose down'
        sh 'docker-compose up -d'
      }
    }
    stage('Deploy Master'){
      when {
        expression { BRANCH_NAME == 'master' }
      }
      environment {
        BOT_CONFIG_FILE = credentials('')
      }
      steps {
        sh 'docker-compose down'
        sh 'docker-compose up -d'
      }
    }
  }
}