# In a real-world scenario, these would use official SDKs or robust CLI wrappers.
# For this agent, they will generate the standard CLI commands for each platform.

class VercelSkills:
    @staticmethod
    def deploy(prod: bool = True):
        return f"vercel deploy {'--prod' if prod else ''}"

class AWSSkills:
    @staticmethod
    def deploy_s3_website(source_dir: str, bucket_name: str):
        return f"aws s3 sync {source_dir} s3://{bucket_name} --delete"

class GCPSkills:
    @staticmethod
    def deploy_cloud_run(service_name: str, image: str, region: str = "us-central1"):
        return f"gcloud run deploy {service_name} --image {image} --region {region} --platform managed --allow-unauthenticated"

class AzureSkills:
    @staticmethod
    def deploy_static_web_app(source: str = "./", app_name: str = "my-static-app"):
        # Assuming SWA CLI is installed
        return f"swa deploy {source} --app-name {app_name}"

class DigitalOceanSkills:
    @staticmethod
    def deploy_app(spec_path: str):
        return f"doctl apps create --spec {spec_path}"

class CoolifySkills:
    # Coolify is often git-based, so this would be a git push to a specific remote
    @staticmethod
    def deploy(remote_name: str = "coolify", branch: str = "main"):
        return f"git push {remote_name} {branch}"

class DokploySkills:
    # Similar to Coolify, uses git push
    @staticmethod
    def deploy(remote_name: str = "dokploy", branch: str = "main"):
        return f"git push {remote_name} {branch}"

class HostingerSkills:
     # Hostinger often uses FTP or SSH for deployments
    @staticmethod
    def deploy_scp(source: str, destination: str, user_host: str):
        return f"scp -r {source}/* {user_host}:{destination}"

class OVHcloudSkills:
    @staticmethod
    def deploy_cold_archive(source: str, container: str):
        return f"swift upload {container} {source}"

class InterserverSkills:
    # Like Hostinger, typically uses standard protocols
    @staticmethod
    def deploy_rsync(source: str, destination: str, user_host: str):
        return f"rsync -avz {source}/ {user_host}:{destination}"

class RailwaySkills:
    @staticmethod
    def deploy():
        return "railway up"
