from setuptools import find_packages, setup

setup(
    name="noobaa-sa-ci",
    version="0.1",
    packages=find_packages(),
    url="",
    license="MIT",
    author="Noobaa SA QE",
    author_email="ocs-ci@redhat.com",
    description=(
        "Noobaa Standalone(SA) infra is used to deploy, upgrade and destroy NooBaa standalone on "
        "RHEL/CentOS stream platforms"
    ),
    install_requires=["common-ci-utils", "mergedeep", "pynpm", "pyyaml", "requests"],
    entry_points={
        "console_scripts": [
            "noobaa-sa-install=deployment.main:noobaa_sa_install",
        ],
    },
)
