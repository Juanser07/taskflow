
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo 'Obteniendo codigo del repositorio...'
                checkout scm
            }
        }

       // Pendiente: stage('Test') -> pruebas con pytest
        // Pendiente: stage('Build') -> docker compose build
        // Pendiente: stage('Deploy') -> despliegue de servicios
    }
}