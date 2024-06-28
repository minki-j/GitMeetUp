from airflow.providers.github.operators.github import GithubOperator
from github import GithubException
from github import Github as GithubClient

from airflow.exceptions import AirflowException

from airflow.providers.github.hooks.github import GithubHook


class CustomGithubOperator(GithubOperator):
    """
    This custom operator allows you to pass an `if_modified_since` parameter to the header of the request.
    This is useful when you want to fetch only the data that has been modified since a certain date, which can prevent unnecessary rate limiting.
    """
    def __init__(self, if_modified_since=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.if_modified_since = if_modified_since

    def get_conn(self) -> GithubClient:
        """Initiate a new GitHub connection with token and hostname (for GitHub Enterprise)."""
        if self.client is not None:
            return self.client

        conn = self.get_connection(self.github_conn_id)
        access_token = conn.password
        host = conn.host

        # Currently the only method of authenticating to GitHub in Airflow is via a token. This is not the
        # only means available, but raising an exception to enforce this method for now.
        # TODO: When/If other auth methods are implemented this exception should be removed/modified.
        if not access_token:
            raise AirflowException(
                "An access token is required to authenticate to GitHub."
            )

        if not host:
            self.client = GithubClient(login_or_token=access_token)
        else:
            self.client = GithubClient(login_or_token=access_token, base_url=host)

        if self.if_modified_since:
            # Add the header to the underlying requester
            self.client._Github__requester.headers["if-modified-since"] = (
                self.if_modified_since
            )


        return self.client
