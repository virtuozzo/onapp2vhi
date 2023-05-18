import nox


@nox.session
def behave(session):
    session.install(
        "behave==1.2.6",
        "requests==2.27.1",
        "pyyaml==6.0",
        "fabric==2.7.1",
    )
    #session.run("cd", "behave", external=True)
    session.run("behave")
