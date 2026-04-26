class ServerSkills:
    @staticmethod
    def nginx_reverse_proxy(domain: str, proxy_pass: str):
        return f"""
server {{
    listen 80;
    server_name {domain};
    location / {{
        proxy_pass {proxy_pass};
        proxy_set_header Host $host;
    }}
}}
"""

    @staticmethod
    def caddy_config(domain: str, proxy_pass: str):
        return f"{domain} {{\n    reverse_proxy {proxy_pass}\n}}"

    @staticmethod
    def traefik_labels(service_name: str, domain: str):
        return {
            f"traefik.http.routers.{service_name}.rule": f"Host(`{domain}`)",
            f"traefik.http.routers.{service_name}.tls": "true",
            f"traefik.http.routers.{service_name}.tls.certresolver": "myresolver"
        }

    @staticmethod
    def setup_ssl(domain: str, email: str):
        return f"certbot --nginx -d {domain} --non-interactive --agree-tos -m {email}"
