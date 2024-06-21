from modal import App, Image, Volume

app = App("gitmeetup_app")

image = (
    Image.debian_slim(python_version="3.12.2")
    .apt_install()
    .pip_install(
        "requests"
    )
)

vol = Volume.from_name("gitmeetup")
