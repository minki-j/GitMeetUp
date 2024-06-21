# include/modal_operator.py

from airflow.models.baseoperator import BaseOperator
import inspect
import modal

class ModalOperator(BaseOperator):
    """
    Custom Airflow Operator for executing tasks on Modal.
    """

    def __init__(self, client, fn, sandbox_config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self.fn = fn
        self.sandbox_config=sandbox_config

    def execute(self, context):
        # defines the ephemeral Modal app
        app = modal.App(f"airflow-{self.task_id}")

        # converts the Python function object into an executable string
        fn_lines = inspect.getsourcelines(self.fn)[0]
        fn_lines.append(f"{self.fn.__name__}()")
        fn_as_string = "".join(fn_lines)

        # runs the function in a Modal Sandbox with the provided config
        with app.run(client=self.client):
            sb = app.spawn_sandbox(
                "python",
                "-c",
                fn_as_string,
                **self.sandbox_config
            )
            sb.wait()
            return sb.stdout.read()
