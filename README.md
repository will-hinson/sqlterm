<div align="center">
    <img src="https://github.com/will-hinson/sqlterm/blob/main/resources/banner.png?raw=true" />
    <em>A modern command-line client for SQL</em>
</div>

<br />

<div align="center">
    <img src="https://github.com/will-hinson/sqlterm/blob/main/resources/example-session4.png?raw=true" alt="An example SQLTerm session" />
</div>

## Installation
The latest release version of SQLTerm may be installed from [PyPI](https://pypi.org/project/sqlterm/) using `pip`:

```shell
pip install sqlterm
```

Alternatively, the latest commit may be installed from this repo if preferred:

```
git clone https://github.com/will-hinson/sqlterm.git
cd sqlterm
pip install .
```

## Getting Started
If you installed SQLTerm using `pip`, it should already be in your shell's path:

```shell
sqlterm

# alternatively, run as a module using python
python -m sqlterm
```

## Supported Dialects
The following SQL dialect and driver combinations are fully supported by SQLTerm for queries and autocompletion:

| Dialect              | Driver           | Connection Schema         |
| -------------------- | ---------------- | ------------------------- |
| Microsoft SQL Server | `pyodbc`         | `mssql+pyodbc://`         |
| PostgreSQL           | `psycopg2`       | `postgresql+psycopg2://`  |
| MySQL                | `mysqlconnector` | `mysql+mysqlconnector://` |
| SQLite               | `sqlite`         | `sqlite://`               |
| Oracle SQL           | `oracledb`       | `oracle+oracledb://`      |
| Amazon Redshift      | `psycopg2`       | `redshift+psycopg2://`    |

SQLTerm is integrated with [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy) and any of [its supported dialects](https://docs.sqlalchemy.org/en/20/dialects/) should be supported in theory. However, queries will be limited to a single result set and autocompletion support will be limited to objects in the `INFORMATION_SCHEMA`. 