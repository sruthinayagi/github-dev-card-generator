FROM nginx:alpine

# Copy the index.html
COPY index.html /usr/share/nginx/html/index.html.template

# Add a script to replace the backend URL at runtime
RUN echo 'echo "Replacing BACKEND_URL with ${BACKEND_URL:-http://localhost:8080}"; envsubst "\$BACKEND_URL" < /usr/share/nginx/html/index.html.template > /usr/share/nginx/html/index.html && exec nginx -g "daemon off;"' > /docker-entrypoint.d/40-subst-backend-url.sh && chmod +x /docker-entrypoint.d/40-subst-backend-url.sh

EXPOSE 80
