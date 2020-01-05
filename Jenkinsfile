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
        POSTGRES_HOST = 'postgres'
        BOT_CLIENT_ID = '648333906168381460'
        BOT_CLIENT_TOKEN = credentials('willow_integration_bot_token')
        BOT_GUILD_ID = '605254694314573824'
        BOT_TECH_ROLE = '608155137646657547'
        BOT_ADMIN_ROLE = '651476728744771601'
      }
      steps {
        sh 'docker-compose down'
        withCredentials([usernamePassword(
            credentialsId: 'willow_integration_postgres',
            usernameVariable: 'POSTGRES_USER',
            passwordVariable: 'POSTGRES_PASSWORD')
        ]) {
            sh 'docker-compose up -d'
        }
      }
    }
    stage('Deploy Master'){
      when {
        expression { BRANCH_NAME == 'master' }
      }
      environment {
        POSTGRES_HOST = 'postgres'
        BOT_CLIENT_ID = '653430328177852416'
        BOT_CLIENT_TOKEN = credentials('willow_bot_token')
        BOT_GUILD_ID = '419896766314446868'
        BOT_TECH_ROLE = '430700713794863104'
        BOT_ADMIN_ROLE = '493804274380439572'
      }
      steps {
        sh 'docker-compose down'
        withCredentials([usernamePassword(
            credentialsId: 'willow_postgres',
            usernameVariable: 'POSTGRES_USER',
            passwordVariable: 'POSTGRES_PASSWORD')
        ]) {
            sh 'docker-compose up -d'
        }
      }
    }
  }
}