#!/usr/bin/env python

import subprocess
import os
import sys
import argparse
import csv
import re
import math
import shutil
import tempfile


def parse_args():
  parser = argparse.ArgumentParser(prog='csvq')
  parser.add_argument('file', type=str, nargs='+', help='one or more .csv files')
  parser.add_argument('-q', '--query', type=str, nargs='?', help='run an SQL query')
  parser.add_argument('-i', '--init', action='store_true', help='outputs sqlite3 init script')
  return parser.parse_args(sys.argv[1:])


def snake_case(s):
  return re.sub(r'[^\w]+', '_', s).strip().lower()


def guess_type(s):
  if s.isdigit():
    return 'integer'
  try:
    float(s)
    return 'real'
  except ValueError:
    return 'text'


def guess_widths(s):
  if s.isdigit():
    # right-justifies
    return -(len(s) + 5)
  else:
    return len(s) + 5


def guess_schema(args, file, table):
  '''
  Why is this needed?

  sqlite> select 2 < 10;
  1
  sqlite> select '2' < '10';
  0
  '''
  schema = {}
  schema['table'] = table
  with open(file, 'r') as f:
    reader = csv.reader(f)
    for i, line in enumerate(reader):
      if i == 0:
        schema['names'] = [snake_case(l) for l in line]
        schema['old_names'] = line
      elif i == 1:
        # "sample" by looking at the first row
        schema['types'] = [guess_type(cell) for cell in line]

        # Idea: automatically determine widths by sampling rows. Problem is
        # there's no good way to do this deterministically without reading the
        # entire file. Doing every N rows depends on file length. Reservoir
        # sampling isn't deterministic. Also needed only in interactive mode.

        # schema['widths'] = [guess_widths(cell) for cell in line]
      else:
        break
  return schema


def generate_create_table(schema):
  cols = []
  for n, t in zip(schema['names'], schema['types']):
    # This doesn't work well as it prevents insertion
    # of the header row when the column type is numeric...
    # if n == 'id':
    #   extra = ' primary key'
    # else:
    #   extra = ''
    # cols.append('  "{}" {}{}'.format(n, t, extra))
    cols.append('  "{}" {}'.format(n, t))
  return '''create table {} (
{}
);'''.format(schema['table'], ',\n'.join(cols))


def generate_header_delete(schema):
  return '''delete from {} where {};'''.format(schema['table'], ' and '.join(['"{}" = \'{}\''.format(n, o) for (n, o) in zip(schema['names'], schema['old_names'])]))


def generate_create_index(schema):
  return '\n'.join(['create unique index {}_index on {}({});'.format(n, schema['table'], n) for n in schema['names'] if n == 'id' or n.endswith('_id')])


def generate_db_setup(args):
  '''
  Generates `create table` DDL, `.import`s, header deletion, indices.

  This approach creates tables (so column names can be normalized), loads the
  csv files into them, deletes the header rows (necessary because we created
  the tables already; see https://www.sqlite.org/cli.html#csv_import), then
  creates indices. We can't create primary/foreign keys with this because the
  headers appear in the table as data; see generate_create_table. /facepalm

  Another approach is to use .import to create the tables (which also figures
  out types). The downside is that in order to rename columns or add
  primary/foreign keys, we'd have to copy the entire table or the csv file
  before reading it, which doesn't seem worthwhile. See
  https://www.sqlite.org/lang_altertable.html.

  Other ideas: if we could create foreign keys, look at the names of _id
  fields to figure out table references, Rails-style, e.g. an "entry_id" column
  becomes a foregin key to the "entries" table. https://github.com/jazzband/inflect
  '''

  imports = []
  create_tables = []
  header_deletes = []
  tables_seen = set()
  indices = []

  for full_file_name in args.file:
    if not os.path.isfile(full_file_name):
      print('{} is not a valid file'.format(full_file_name))
      exit(1)

    file_name = os.path.basename(full_file_name)
    (table_name, ext) = os.path.splitext(file_name)
    table_name = snake_case(table_name)

    if table_name in tables_seen:
      print('cannot create table {} twice'.format(table_name))
      exit(1)
    tables_seen.add(table_name)

    imports.append('.import {} {}'.format(full_file_name, table_name))

    schema = guess_schema(args, full_file_name, table_name)
    create_tables.append(generate_create_table(schema))
    header_deletes.append(generate_header_delete(schema))

    # should we always do this, even in non-interactive mode?
    indices.append(generate_create_index(schema))

  setup = '\n'.join(create_tables + imports + header_deletes + indices)
  return setup, '\n'.join(create_tables), next(iter(tables_seen))


def main():

  args = parse_args()

  interactive = not (args.query or args.init)
  query = args.query or ''

  setup, create_tables, some_table = generate_db_setup(args)

  if interactive:
    output = '.mode columns'
  else:
    output = '.output stdout'
    if query and not query.endswith(';'):
      query = query + ';'

  sqlite_command = '''
.headers on
.mode csv
{}
{}
{}
'''.format(setup, output, query).strip()
  # lack of hygiene for the query here was intentional at some point, probably so there can be multiple queries?

  # this interacts badly with attempts to save
  #   bling = '''
  # .nullvalue ⊥
  # '''

  # TODO cache db in tempfile.gettempdir() using sha1 of input files (in other).
  # speedup doesn't seem worth the increase in complexity so far

  if args.query:
    # this will inherit stdout/stderr
    process = subprocess.Popen(['sqlite3'], stdin=subprocess.PIPE, shell=False)
    process.communicate(input=bytes(sqlite_command, 'utf-8'))
  elif args.init:
    print(sqlite_command)
  else:
    print('''
{}

To save results:

.mode csv
.output out.csv
select * from {};
'''.format(create_tables, some_table))
    sqlite = shutil.which('sqlite3')
    with tempfile.NamedTemporaryFile() as f:
      f.write(sqlite_command.encode('utf-8'))
      f.flush()
      os.execv(sqlite, [sqlite, '-init', f.name])
    # https://docs.python.org/3/library/tempfile.html#tempfile.TemporaryFile
    # note that the file is not deleted, as it is never closed due to the execv
