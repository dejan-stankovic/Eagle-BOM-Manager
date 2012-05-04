import types
import sqlite3
from manager import Workspace
from product import Product

class Part:
	''' A self in the BOM exported from Eagle. '''
	
	@staticmethod
	def new_from_row(row, wspace, connection=None, known_project=None):
		from bom import BOM
		''' Given a part row from the DB, returns a Part object. '''
		#print 'new_from_row: row param: ', row
		if row[6] is None or row[6] == 'NULL' or row[6] == '':
			product = None
			#print 'new_from_row: setting no product'
		else:
			product = Product.select_by_pn(row[6], wspace, connection)[0]
			#print 'new_from_row: product results: ', product
		if row[1] is None or row[1] == 'NULL':
			project = None # TODO: Raise an exception here? This is a PK  violation
			print 'row[1] is None/NULL!'
		else:
			if known_project is None:
				projects = BOM.read_from_db(row[1], wspace, connection)
				if len(projects) > 0:
					project = projects[0]
			else:
				project = known_project
		part = Part(row[0], project, row[2], row[3], row[4], row[5], product)
		part.fetch_attributes(wspace, connection)
		if project.name == 'test3':
			#if row[0] == 'C5' or row[0] == 'C63':
			print 'new_from_row returning part (row[0] = %s) ' % row[0]
				#part.show()
		return part
	
	@staticmethod
	def select_all(wspace, connection=None):
		''' Returns the entire parts table. '''
		print 'Entered Part.select_all'
		parts = []
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			cur.execute('SELECT * FROM parts')
			rows = cur.fetchall()
			print 'Rows: ', type(rows), rows
			for row in rows:
				part = Part.new_from_row(row, wspace, con)
				#print 'Appending part: ', part.show()
				parts.append(part)
		
		finally:
			cur.close()
			if connection is None:
				con.close()
			return parts
	
	@staticmethod
	def select_by_name(name, wspace, project='*', connection=None):
		''' Return the Part(s) of given name. '''
		parts = []
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			sql = "SELECT * FROM parts WHERE name=? and project='%s'" % project
			params = (name,)
			cur.execute(sql, params)
			for row in cur.fetchall():
				parts.append(Part.new_from_row(row, wspace, con))
			
		finally:
			cur.close()
			if connection is None:
				con.close()
			return parts
	
	@staticmethod
	def select_by_value(val, wspace, project='*', connection=None):
		''' Return the Part(s) of given value in a list. '''
		parts = []
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			sql = "SELECT * FROM parts WHERE value=? and project='%s'" % project
			params = (val,)
			cur.execute(sql, params)
			for row in cur.fetchall():
				parts.append(Part.new_from_row(row, wspace, con))
			
		finally:
			cur.close()
			if connection is None:
				con.close()
			return parts
		
	@staticmethod
	def select_by_product(prod, wspace, project='*', connection=None):
		''' Return the Part(s) of given product in a list. '''
		parts = []
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			sql = "SELECT * FROM parts WHERE product=? and project='%s'" % project
			params = (prod,)
			cur.execute(sql, params)
			for row in cur.fetchall():
				parts.append(Part.new_from_row(row, wspace, con))
			
		finally:
			cur.close()
			if connection is None:
				con.close()
			return parts
	
	def __init__(self, name, project, value, device, package, description=None, product=None, attributes={}):
		self.name = name
		self.project = project	# A BOM object
		self.value = value
		self.device = device
		self.package = package
		self.description = description
		self.product = product	# A Product object
		self.attributes = attributes

	def show(self):
		''' A simple print method. '''
		print 'Name: ', self.name, type(self.name)
		print 'Project name: ', self.project.name, type(self.project)
		print 'Value: ', self.value, type(self.value)
		print 'Device: ', self.device, type(self.device)
		print 'Package: ', self.package, type(self.package)
		print 'Description: ', self.description, type(self.description)
		if self.product is not None:
			print 'Product PN: ', self.product.manufacturer_pn, type(self.product.manufacturer_pn)
		for attrib in self.attributes.items():
			print attrib[0], ': ', attrib[1]
		
	def equals(self, p, check_foreign_attribs=True, same_name=True, same_project=True, same_product=True):
		''' Compares the Part to another Part.
		The check_foreign_attribs argument (default True) controls whether or not
		p.attributes.keys() is checked for members not in self.attributes.keys().
		The reverse is always checked. '''
		if type(p) != type(self):
			return False
		eq = True
		if same_name is True and self.name != p.name:
			eq = False
		elif same_project is True and self.project.name != p.project.name:
			eq = False
		elif self.value != p.value:
			eq = False
		elif self.device != p.device:
			eq = False
		elif self.package != p.package:
			eq = False
		elif self.description != p.description:
			eq = False
		elif same_product is True:
			if self.product is None or p.product is None:
				if self.product is not p.product:
					eq = False
			elif self.product.manufacturer_pn != p.product.manufacturer_pn:
				eq = False
		if self.attributes is not None:
			for k in self.attributes.keys():
				if self.attributes[k] != "":
					if k not in p.attributes.keys():
						eq = False
					elif self.attributes[k] != p.attributes[k]:
						eq = False
					
		if check_foreign_attribs is True:
			if p.attributes is None and self.attributes is not None:
				eq = False
			else:
				for k in p.attributes.keys():
					if p.attributes[k] != "":
						if k not in self.attributes.keys():
							eq = False
						elif p.attributes[k] != self.attributes[k]:
							eq = False
		return eq
		

	def findInFile(self, bom_file):
		''' Check if a BOM self of this name is in the given CSV BOM. '''
		with open(bom_file, 'rb') as f:
			db = csv.reader(f, delimiter=',', quotechar = '"', quoting=csv.QUOTE_ALL)
			rownum = 0
			for row in db:
				if row[0] == self.name:
					return rownum
				rownum = rownum + 1
			return -1
	
	def find_similar_parts(self, wspace, check_wspace=True, connection=None):
		''' Search the project and optionally workspace for parts of matching value/device/package/attributes.
		If check_wspace = True, returns a pair of lists: (project_results, workspace_results).
		If check_wspace = False, only returns the project_results list. 
		This allows for parts in different projects that incidentally have the same name to be added.
		Only returns parts that have all of the non-empty attributes in self.attributes
		(with equal values). This behavior is equivalent to self.equals(some_part, False). '''
		if self.name == 'C5' and self.project.name == 'test2': # debug
			print 'Entering %s.%s.find_similar_parts' % (self.project.name, self.name)
		project_results = set()
		workspace_results = set()
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()

			sql = '''SELECT * FROM parts WHERE value=? AND device=? AND package=? AND project=? AND name IN 
			(SELECT part FROM part_attributes WHERE part!=? AND project=? AND name IN 
				(SELECT name FROM part_attributes WHERE part=? AND project=?) 
				OR NOT EXISTS 
				(SELECT name FROM part_attributes WHERE part=? AND project=?) 
			INTERSECT 
			SELECT part FROM part_attributes WHERE part!=? AND project=? AND value IN 
				(SELECT value FROM part_attributes WHERE part=? AND project=?) 
				OR NOT EXISTS 
				(SELECT value FROM part_attributes WHERE part=? AND project=?))''' 
			params = (self.value, self.device, self.package, self.project.name, \
					self.name, self.project.name, self.name, self.project.name, self.name, self.project.name, \
					self.name, self.project.name, self.name, self.project.name, self.name, self.project.name,)

			if self.name == 'C5' and self.project.name == 'test2': # debug
				print 'Executing project query'
			cur.execute(sql, params)
			if self.name == 'C5' and self.project.name == 'test2': # debug
				print 'Executed project query'
			rows = cur.fetchall()
			for row in rows:
				if self.name == 'C5' and self.project.name == 'test2': # debug
					print 'Found row in project: ', row
				part = Part.new_from_row(row, wspace, con)
				project_results.add(part)
					
			if check_wspace:
				#view3 = 'CREATE VIEW other_wspace_attributes AS SELECT * FROM part_attributes WHERE project!=?'
				sql = '''SELECT * FROM parts WHERE value=? AND device=? AND package=? AND project!=? AND name IN 
				(SELECT part FROM part_attributes WHERE project!=? AND name IN 
					(SELECT name FROM part_attributes WHERE part=? AND project=?) 
					OR NOT EXISTS 
					(SELECT name FROM part_attributes WHERE part=? AND project=?) 
				INTERSECT 
				SELECT part FROM part_attributes WHERE project!=? AND value IN 
					(SELECT value FROM part_attributes WHERE part=? AND project=?) 
					OR NOT EXISTS 
					(SELECT value FROM part_attributes WHERE part=? AND project=?))''' 
				params = (self.value, self.device, self.package, self.project.name, \
						self.project.name, self.name, self.project.name, self.name, self.project.name, \
						self.project.name, self.name, self.project.name, self.name, self.project.name,)
				if self.name == 'C5' and self.project.name == 'test2': # debug
					print 'selecting other_wspace_attributes'
				cur.execute(sql, params)
				if self.name == 'C5' and self.project.name == 'test2': # debug
					print 'selected other_wspace_attributes'
				rows = cur.fetchall()
				for row in rows:
					if self.name == 'C5' and self.project.name == 'test2': # debug
						print 'Found row in workspace: ', row
					part = Part.new_from_row(row, wspace, con)
					workspace_results.add(part)
							
		finally:
			cur.close()
			if connection is None:
				con.close()
			if check_wspace:
				return (list(project_results), list(workspace_results))
			else:
				return (list(project_results), [])
	
	def find_matching_products(self, wspace, proj_parts, wspace_parts, connection=None):
		''' Takes in the output of self.find_similar_parts. 
		Returns a list of Product objects.'''
		# TODO : Find more results by searching the product_attributes table
		products = set()
		part_nums = set()
		for part in proj_parts:
			if part.product is not None:
				db_prods = Product.select_by_pn(part.product.manufacturer_pn, wspace, connection)
				for prod in db_prods:
					if prod.manufacturer_pn not in part_nums:
						part_nums.add(prod.manufacturer_pn)
						products.add(prod)
		
		for part in wspace_parts:
			if part.product is not None:
				db_prods = Product.select_by_pn(part.product.manufacturer_pn, wspace, connection)
				for prod in db_prods:
					if prod.manufacturer_pn not in part_nums:
						part_nums.add(prod.manufacturer_pn)
						products.add(prod)
	
		return list(products)
	
	def is_in_db(self, wspace, connection=None):
		''' Check if a BOM self of this name is in the project's database. '''
		result = Part.select_by_name(self.name, wspace, self.project.name, connection)
		if len(result) == 0:
			return False
		else:
			return True
	
	def product_updater(self, wspace, connection=None, check_wspace=True):
		''' Checks if the Part is already in the DB. 
		Inserts/updates self into DB depending on:
		- The presence of a matching Part in the DB
		- The value of self.product.manufacturer_pn
		- The product of the matching Part in the DB
		Passing an open connection to this method is recommended. '''
		if self.name == 'C5' and self.project.name == 'test2': # debug
			print 'Entering %s.%s.product_updater' % (self.project.name, self.name)
		unset_pn = ('', 'NULL', 'none', None, [])
		#self.show()
		if(self.is_in_db(wspace, connection)):
			if self.name == 'C5' and self.project.name == 'test2': # debug
				print "Part of same name already in DB"
			old_part = Part.select_by_name(self.name, wspace, self.project.name, connection)[0]
			#old_part.show()
			if(self.value == old_part.value and self.device == old_part.device and self.package == old_part.package):
				if self.product is not None and self.product.manufacturer_pn not in unset_pn:
					if old_part.product is not None and old_part.product.manufacturer_pn not in unset_pn:
						# TODO: prompt? Defaulting to old_part.product for now (aka do nothing)
						#print 'Matching CSV and DB parts with non-NULL product mismatch, keeping DB version...'
						pass
					elif old_part.product is None or old_part.product.manufacturer_pn in unset_pn:
						self.update(wspace, connection)
				elif self.product is None or self.product.manufacturer_pn in unset_pn:
					if old_part.product is not None and old_part.product.manufacturer_pn not in unset_pn:
						pass	# Do nothing in this case
					elif old_part.product is None or old_part.product.manufacturer_pn in unset_pn:
						(candidate_proj_parts, candidate_wspace_parts) = self.find_similar_parts(wspace, check_wspace, connection)
						if self.name == 'C5' and self.project.name == 'test2': # debug
							print 'first find_similar_parts call'
							print 'candidate_proj_parts: ', candidate_proj_parts
							print 'candidate_wspace_parts: ', candidate_wspace_parts
						candidate_products = self.find_matching_products(wspace, candidate_proj_parts, candidate_wspace_parts, connection)
						if len(candidate_products) == 0:
							#print 'No matching products found, nothing to do'
							pass
						elif len(candidate_products) == 1:
							self.product = candidate_products[0]
							#print 'Found exactly one matching product, setting product and updating', #self.show()
							self.update(wspace, connection)
						else:
							#print 'Found multiple product matches, prompting for selection...'
							# TODO: Currently going with first result, need to prompt for selection
							self.product = candidate_products[0]
							self.update(wspace, connection)
						
			else:	# Value/device/package mismatch
				if self.product is not None and self.product.manufacturer_pn not in unset_pn:
					self.update(wspace, connection)
				elif self.product is None or self.product.manufacturer_pn in unset_pn:
					(candidate_proj_parts, candidate_wspace_parts) = self.find_similar_parts(wspace, check_wspace, connection)
					if self.name == 'C5' and self.project.name == 'test2': # debug
						print 'second find_similar_parts call'
						print 'candidate_proj_parts: ', candidate_proj_parts
						print 'candidate_wspace_parts: ', candidate_wspace_parts
					candidate_products = self.find_matching_products(wspace, candidate_proj_parts, candidate_wspace_parts, connection)
					if len(candidate_products) == 0:
						if self.name == 'C5' and self.project.name == 'test2': # debug
							print 'No matching products found, updating as-is'
						#pass
					elif len(candidate_products) == 1:
						self.product = candidate_products[0]
						#print 'Found exactly one matching product, setting product and updating'#, self.show()
					else:
						#print 'Found multiple product matches, prompting for selection...'
						# TODO: Currently going with first result, need to prompt for selection
						self.product = candidate_products[0]
					self.update(wspace, connection)
		
		else:
			if self.name == 'C5' and self.project.name == 'test2': # debug
				print 'Part not in DB'
			if self.product is None or self.product.manufacturer_pn in unset_pn:
				(candidate_proj_parts, candidate_wspace_parts) = self.find_similar_parts(wspace, check_wspace, connection)
				if self.name == 'C5' and self.project.name == 'test2': # debug
					print 'third find_similar_parts call'
					print 'candidate_proj_parts: ', candidate_proj_parts
					print 'candidate_wspace_parts: ', candidate_wspace_parts
				candidate_products = self.find_matching_products(wspace, candidate_proj_parts, candidate_wspace_parts, connection)
				if len(candidate_products) == 0:
					if self.name == 'C5' and self.project.name == 'test2': # debug
						print 'No matching products found, inserting as-is'#, self.show()
					pass
				elif len(candidate_products) == 1:
					self.product = candidate_products[0]
					if self.name == 'C5' and self.project.name == 'test2': # debug
						print 'Found exactly one matching product, setting product and inserting'#, self.show()
				else:
					#print 'Found multiple product matches, prompting for selection...'
					# TODO: Currently going with first result, need to prompt for selection
					self.product = candidate_products[0]
			else:
				if self.product.is_in_db(wspace, connection) == False:
					newprod = Product('NULL', self.product.manufacturer_pn)
					newprod.insert(wspace, connection)
					newprod.scrape(wspace, connection)
			self.insert(wspace, connection)
		
	def update(self, wspace, connection=None):
		''' Update an existing Part record in the DB. '''
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			if self.product is None:
				pn = 'NULL'
			else:
				pn = self.product.manufacturer_pn
			
			sql = 'UPDATE parts SET name=?, project=?, value=?, device=?, package=?, description=?, product=? WHERE name=? AND project=?'
			params = (self.name, self.project.name, self.value, self.device, self.package,  
					self.description, pn, self.name, self.project.name,)
			cur.execute(sql, params)
			self.write_attributes(wspace, con)
			
		finally:
			cur.close()
			if connection is None:
				con.close()
	
	def insert(self, wspace, connection=None):
		''' Write the Part to the DB. '''
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			if self.product is None:
				pn = 'NULL'
			else:
				pn = self.product.manufacturer_pn
			
			sql = 'INSERT OR REPLACE INTO parts VALUES (?,?,?,?,?,?,?)'
			params = (self.name, self.project.name, self.value, self.device, self.package,  
					self.description, pn,)
			cur.execute(sql, params)
			self.write_attributes(wspace, con)
			
		finally:
			cur.close()
			if connection is None:
				con.close()
	
	def delete(self, wspace, connection=None):
		''' Delete the Part from the DB. 
		Part attributes are deleted via foreign key constraint cascading. '''
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			sql = 'DELETE FROM parts WHERE name=? AND project=?'
			params = (self.name, self.project.name)
			cur.execute(sql, params)
			
		finally:
			cur.close()
			if connection is None:
				con.close()
	
	def fetch_attributes(self, wspace, connection=None):
		''' Fetch attributes dictionary for this Part. 
		Clears and sets the self.attributes dictionary directly. '''
		self.attributes.clear()
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			params = (self.name, self.project.name,)
			#cur.execute('''SELECT name, value FROM part_attributes WHERE part=? INTERSECT 
			#SELECT name, value FROM part_attributes WHERE project=?''', params)
			cur.execute('SELECT name, value FROM part_attributes WHERE part=? AND project=?', params)
			for row in cur.fetchall():
				self.attributes[row[0]] = row[1]
			
		finally:
			cur.close()
			if connection is None:
				con.close()
	
	def has_attribute(self, attrib, wspace, connection=None):
		'''Check if this Part has an attribute of given name in the DB. 
		Ignores value of the attribute. '''
		results = []
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			params = (self.name, self.project.name, attrib,)
			cur.execute('''SELECT name FROM part_attributes WHERE part=? INTERSECT 
			SELECT name FROM part_attributes WHERE project=? INTERSECT 
			SELECT name FROM part_attributes WHERE name=?''', params)
			for row in cur.fetchall():
				results.append(row[0])
			
		finally:
			cur.close()
			if connection is None:
				con.close()
			if len(results) == 0:
				return False
			else:
				return True
	
	def add_attribute(self, name, value, wspace, connection=None):
		''' Add a single attribute to this Part.
		Adds the new attribute to the self.attributes dictionary in memory.
		Writes the new attribute to the DB immediately. '''
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			self.attributes[name] = value
			params = (self.name, self.project.name, name, value,)
			cur.execute('INSERT OR REPLACE INTO part_attributes VALUES (NULL,?,?,?,?)', params)

		finally:
			cur.close()
			if connection is None:
				con.close()
				
	def remove_attribute(self, name, wspace, connection=None):
		''' Removes a single attribute from this Part.
		Deletes the attribute from the self.attributes dictionary in memory.
		Deletes the attribute from the DB immediately. '''
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			if name in self.attributes:
				del self.attributes[name]
			params = (self.name, self.project.name, name,)
			cur.execute('DELETE FROM part_attributes WHERE part=? AND project=? AND name=?', params)

		finally:
			cur.close()
			if connection is None:
				con.close()

	def write_attributes(self, wspace, connection=None):
		''' Write all of this Part's attributes to the DB.
		Checks attributes currently in DB and updates/inserts as appropriate. '''
		# TODO: This does not remove any old attribs from the DB that are not in solf.attributes
		db_attribs = []
		old_attribs = []
		new_attribs = []
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			params = (self.name, self.project.name,)
			#cur.execute('''SELECT name FROM part_attributes WHERE part=? INTERSECT 
			#SELECT name FROM part_attributes WHERE project=?''', params)
			cur.execute('SELECT name FROM part_attributes WHERE part=? AND project=?', params)
			for row in cur.fetchall():
				db_attribs.append(row[0])
			for a in self.attributes.items():
				if a[1] != "":
					if a[0] in db_attribs:
						old_attribs.append((a[1], self.name, self.project.name, a[0],))
					else:
						new_attribs.append((self.name, self.project.name, a[0], a[1],))
			if self.project.name == 'test2' and self.name == 'C5':
				print 'db_attribs: ', db_attribs
				print 'old_attribs: ', old_attribs
				print 'new_attribs: ', new_attribs
			cur.executemany('INSERT OR REPLACE INTO part_attributes VALUES (NULL,?,?,?,?)', new_attribs)
			cur.executemany('UPDATE part_attributes SET value=? WHERE part=? AND project=? AND name=?', old_attribs)
		
		finally:
			cur.close()
			if connection is None:
				con.close()
