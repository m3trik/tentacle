# !/usr/bin/python
# coding=utf-8
from __future__ import print_function, absolute_import
import sqlite3
from sqlite3 import Error



class Database():
	'''Create and/or connect to an SQLite database.
	'''
	def __init__(self, database):
		'''
		:Parameters:
			database (str) = An absoute path to a database file. 
							':memory:' will create a new database that resides in RAM instead of a file on disk.
							If you just give a filename, the program will create the database file in the current working directory.
		'''
		self.conn = sqlite3.connect(database)
		if self.conn:
			self.cur = self.conn.cursor()
		else:
			raise Exception("Error: Cannot create a database connection.")


	def create_table(self, name, *args, **kwargs):
		'''Create a table.

		:Parameters:
			name (str) = The table's name.
			*args (str) = The table's contents. ex. 'cmd text PRIMARY KEY'
			silent (bool) = Prevent printing the table structure to the console on creation. (default=False)

		ex. db.create_table('cmds', 'cmd text PRIMARY KEY', 'doc text NOT NULL')
		'''
		table = '''
			CREATE TABLE IF NOT EXISTS {table} (
			{content}
			)
			'''.format(table=name, content=',\n'.join(args))

		try:
			self.cur.execute(table)

			silent = kwargs['silent'] = kwargs.get('silent', False) # if bar is not set use foo as val
			if not silent:
				print (table.replace('	', ''))
		except Exception as e:
			print (e)


	def insert(self, table, *args, **kwargs):
		'''Insert values into a table.

		:Parameters:
			table (str) = Table.
			args (list) = Column values.
			kwargs (dict) = Column:Value pairs for assigning values to specific columns.

		:Return:
			(int) the value generated for a column during the last INSERT or, UPDATE operation.

		ex. task1_id = db.insert('tasks', name='', priority=1, status_id=1, project_id=proj_id, begin_date='', end_date='')
		'''
		columns = '' #omit the columns argument if no columns are given.
		if kwargs.keys():
			columns = '('+', '.join(str(i) for i in kwargs.keys())+')'

		values  = ', '.join('"'+str(i)+'"' for i in kwargs.values()+list(args))

		sql = '''
			INSERT INTO {table} {columns}
			VALUES ({values});
			'''.format(table=table, columns=columns, values=values)

		self.cur.execute(sql)
		self.conn.commit()

		return self.cur.lastrowid


	def update(self, table, condition=None, *args, **kwargs):
		'''Update all values of a table, or those matching a given condition.

		:Parameters:
			table (str) = table. 
			condition (str) = SQL condition statement. You can combine any number of conditions using AND or OR operators.
			kwargs (dict) = column:value pairs for assigning values to specific columns.
		'''
		kw_item_value_pairs = ('{}={}'.format(k,v) for k,v in kwargs.items())

		formatted_kwargs = ', '.join('"'+str(i)+'"' for i in kw_item_value_pairs)
		formatted_args = ', '.join('"'+str(i)+'"' for i in args)

		values = formatted_args+', '+formatted_kwargs if args else formatted_kwargs

		if condition:
			sql = '''
				UPDATE {table}
				SET ({values})
				WHERE {condition}
				'''.format(table=table, values=values, condition=condition)
		else:
			sql = '''
				UPDATE {table}
				SET ({values})
				'''.format(table=table, values=values)

		self.cur.execute(sql)
		self.conn.commit()


	def select(self, table, column='*', condition=None, flatten=True):
		'''Select all of a table's content, or those matching a given condition.

		:Parameters:
			table (str) = The table(s) in which to perform the selection.
			column (str) = The column(s) to pull from.
			condition (str) = SQL condition statement. You can combine any number of conditions using AND or OR operators.
			flatten (bool) = Flatten the resulting list of tuples to a single list.

		:Return:
			(list)

		ex. sel = db.select('polyReduce', 'param IS "__doc__"')
		ex. sel = db.select(<table>, '<column> LIKE "%nurbs%"') #select all rows in <table> table where <column> contains the string 'nurbs'.
		'''
		if condition:
			sql = 'SELECT {column} FROM {table} WHERE {condition}'.format(column=column, table=table, condition=condition)
		else:
			sql = 'SELECT {column} FROM {table}'.format(column=column, table=table)

		self.cur.execute(sql)

		rows = self.cur.fetchall()
		if flatten:
			rows = [i for sublist in rows for i in sublist]

		return rows


	def delete(self, table, condition=None):
		'''Delete all rows, or those matching a given condition.

		:Parameters:
			table (str) = The table in which to perform the delete operation.
			condition (str) = SQL condition statement. You can combine any number of conditions using AND or OR operators.
		
		ex. db.delete(<table>) #delete all rows of the given table.
		ex. db.delete('cmds', 'cmd IS polyReduce') #delete the row in the cmds table where the cmd column value is 'polyReduce'.
		'''
		if condition:
			sql = 'DELETE FROM {table} WHERE {condition}'.format(table=table, condition=condition)
		else:
			sql = 'DELETE FROM {table}'.format(table=table)

		self.cur.execute(sql)
		self.conn.commit()


	def disconnect(self):
		'''Disconnect from the database.
		'''
		try:
			self.conn.close()
		except Exception as e:
			print (e)









if __name__ == '__main__':
	#example use-case:
	import json #use json to coerce varying datatypes to and from string values.
	db = Database(r'database_name.db') #create of connect to an existing database.

	db.create_table(
		'table_name',
		'param text NOT NULL', #column | datatype | condition
		'value varchar NOT NULL',
		silent=True, #Prevent printing the table structure to the console on creation. (default=False)
	)

	table_id = db.insert('table_name', param='__doc__', value='docstring') #insert values to the given columns.
	table_id = db.insert('table_name', param='parameter', value=json.dumps(0.5)) #serialize the float value using json.

	sel = db.select('table_name', 'value', 'param IS "parameter"')
	print (sel, type(json.loads(sel[0]))) #de-serialize the value back to a float.

	db.delete('table_name') #delete the table.
	db.disconnect()