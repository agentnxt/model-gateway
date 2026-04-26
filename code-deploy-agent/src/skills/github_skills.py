class GitHubSkills:
    @staticmethod
    def init_repo():
        return "git init"

    @staticmethod
    def commit_all(message: str):
        return f"git add . && git commit -m '{message}'"

    @staticmethod
    def create_pr(title: str, body: str):
        return f"gh pr create --title '{title}' --body '{body}'"

    @staticmethod
    def clone_repo(url: str):
        return f"git clone {url}"
