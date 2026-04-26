import subprocess

class DockerSkills:
    @staticmethod
    def run_container(image: str, name: str, ports: dict = None, env: dict = None):
        cmd = ["docker", "run", "-d", "--name", name]
        if ports:
            for p_host, p_cont in ports.items():
                cmd.extend(["-p", f"{p_host}:{p_cont}"])
        if env:
            for key, val in env.items():
                cmd.extend(["-e", f"{key}={val}"])
        cmd.append(image)
        return " ".join(cmd)

    @staticmethod
    def run_autonomyx_model(model_name: str, version: str = "latest"):
        # Specialized autonomyx model runner logic
        image = f"autonomyx/{model_name}:{version}"
        return f"docker run -d --name {model_name}-runner {image}"

    @staticmethod
    def get_compose_template(service_name: str, image: str, port: int):
        return f"""
services:
  {service_name}:
    image: {image}
    ports:
      - "{port}:{port}"
    restart: always
"""
