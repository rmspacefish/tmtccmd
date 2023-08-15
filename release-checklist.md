Checklist for new releases
========

# Pre-Release

1. Make sure the docs build with Sphinx, using `make html` inside the
   `docs` directory with dependencies in `docs/requirements.txt` installed.
2. Bump version inside the `tmtccmd/__init__.py` file.
3. Update `CHANGELOG.md`: Convert `unreleased` section into version section
   with date and new `unreleased`section.
4. Run tests with `pytest .`
5. Run auto-formatter with `black .`
6. Run linter script `./lint.py`
7. Wait for CI/CD results. This also runs the tests on different
   operating systems

# Post-Release

1. Create new release on [GitHub](https://github.com/robamu-org/tmtccmd) based on the release
   branch. This also creates a tag.
