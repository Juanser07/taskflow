
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo 'Obteniendo codigo del repositorio...'
                checkout scm
            }
        }

        stage('Test') {
            steps {
                echo 'Preparando entorno de pruebas...'

                sh '''
                    python3 -m venv .venv
                    .venv/bin/python -m pip install --upgrade pip
                    .venv/bin/python -m pip install -r api/requirements.txt
                '''

                echo 'Ejecutando pruebas automatizadas...'

                sh '''
                    cd api
                    ../.venv/bin/python -m pytest -v
                '''
            }
        }

        stage('Build') {
            steps {
                echo 'Construyendo las imágenes Docker de TaskFlow...'
                sh 'docker compose build'
            }
        }
        // Pendiente: stage('Deploy') -> despliegue de servicios
    }
}
