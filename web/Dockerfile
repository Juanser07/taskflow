# Contenedor "web": Nginx sirve el frontend y hace de proxy inverso hacia la API
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html styles.css app.js /usr/share/nginx/html/

EXPOSE 80
