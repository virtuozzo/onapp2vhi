import nox
import os


@nox.session
def lint(session):
    session.install("pylint==2.13.9", "mock==5.0.1", "requests-mock==1.10.0", ".")
    session.run("pylint", "-E", "onapp2vhi/", "tests/")


@nox.session
def style(session):
    session.install("flake8==3.9.2")
    session.run("flake8", "onapp2vhi/", "tests/")


@nox.session
def unittest(session):
    session.install("nose==1.3.7", "mock==5.0.1", "requests-mock==1.10.0", ".")
    session.run("nosetests", "-xsv")

@nox.session
def code_coverage(session):
    session.install("nox==2022.1.7", "nose==1.3.7", "mock==5.0.1", "requests-mock==1.10.0", "coverage==6.2", ".")
    try:
        os.remove(os.path.join(os.getcwd(), '.coverage'))
    except OSError:
        pass
    session.run("nosetests", "--with-coverage", "--cover-inclusive")
    session.run("coverage", "report")
    session.run("coverage", "html")

@nox.session
def behave(session):
    session.install(
        "behave==1.2.6",
        "requests==2.27.1",
        "pyyaml==6.0",
        "fabric==2.7.1",
    )
    session.cd("behave")
    session.run("behave")
