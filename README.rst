|pypi| |actions| |uv| |ruff| |codecov| |downloads| |clinicedc|

parse-trial-labs
================

Parsers
-------

* ``parse_mnh``: Parse Muhimbili National Hospital lab result PDFs


To get an App Password for a Gmail account:

Go to myaccount.google.com

Security (left sidebar)

Under "How you sign in to Google", confirm 2-Step Verification is on (required — you can't create app passwords without it)

Search for "App Passwords" in the search bar at the top, or navigate to Security > 2-Step Verification > App Passwords

Enter a name (e.g. "lab results download") and click Create

Google shows a 16-character password — copy it immediately, you won't see it again

That 16-character password is what the script will use in place of your regular Gmail password.

Running tests
-------------

    uv sync --dev
    uv run --dev pytest

.. |pypi| image:: https://img.shields.io/pypi/v/parse-trial-labs.svg
    :target: https://pypi.python.org/pypi/parse-trial-labs

.. |actions| image:: https://github.com/erikvw/parse-trial-labs/actions/workflows/build.yml/badge.svg
  :target: https://github.com/erikvw/parse-trial-labs/actions/workflows/build.yml

.. |codecov| image:: https://codecov.io/gh/erikvw/parse-trial-labs/branch/develop/graph/badge.svg
  :target: https://codecov.io/gh/erikvw/parse-trial-labs

.. |downloads| image:: https://pepy.tech/badge/parse-trial-labs
   :target: https://pepy.tech/project/parse-trial-labs

.. |clinicedc| image:: https://img.shields.io/badge/framework-Clinic_EDC-green
   :alt:Made with clinicedc
   :target: https://github.com/clinicedc

.. |uv| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json
  :target: https://github.com/astral-sh/uv

.. |ruff| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://github.com/astral-sh/ruff
    :alt: Ruff
