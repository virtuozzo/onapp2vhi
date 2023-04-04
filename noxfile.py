import nox


@nox.session
def lint(session):
    session.install("pylint==2.13.9", ".")
    session.run("pylint", "-E", "onapp2vhi/", "inc/", "cfg/")


@nox.session
def style(session):
    session.install("flake8==3.9.2")
    session.run("flake8", "onapp2vhi/", "inc/", "cfg/")
