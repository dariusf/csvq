
Glue for manipulating CSV files in shell pipelines.

- Less fragile than using `cut` or `awk` to extract columns
- Full SQL (joins, subqueries, CTEs, etc.)
- Requires Python 3.5.2+ and `sqlite3`

## Usage

```sh
$ csv a.csv -q 'select * from a'
```

This runs an SQL query on the given file(s) and writes CSV to stdout.

- Files map to tables and are expected to have headers
- Table and column names are snake_cased so they don't have to be quoted
- Column types are guessed from the first row
- `id` and `*_id` columns are indexed

If you need to perform more than a single query, load your data into SQLite:

```sh
$ csv a.csv
```

## Installation

```sh
pip install git+https://github.com/dariusf/csvq.git
```
