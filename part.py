import types
import sqlite3
from manager import Workspace
from product import Product

class Part:
	''' A self in the BOM exported from Eagle. '''
	
	@staticmethod
	def new_from_row(row, wspace, connection=None, known_project=None):
		''' Given a part row from the DB, returns a Part object. '''
		from bom import BOM
		if row[0] == 'C63' or row[0] == 'C58':
			print 'Part.new_from_row passed row: ', row
		
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
		#if project.name == 'test3' and (row[0] == 'C5' or row[0] == 'C63'):
		if row[0] == 'C63' or row[0] == 'C58':
			print 'new_from_row returning part (row[0] = %s) ' % row[0]
			print part
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
	
	def __init__(self, name, project, value, device, package, description=None, product=None, attributes=None):
		self.name = name
		self.project = project	# A BOM object
		self.value = value
		self.device = device
		self.package = package
		self.description = description
		self.product = product	# A Product object
		if attributes is None:
			self.attributes = dict()
		else:
			self.attributes = attributes

	def __str__(self):
		if self.product is None:
			return '%s.%s (%s, %s, %s): No product, Attribs: %s' % (self.project.name, self.name, self.value, self.device, self.package, self.attributes)
		else:
			return '%s.%s (%s, %s, %s): PN: %s, Attribs: %s' % (self.project.name, self.name, self.value, self.device, self.package, self.product.manufacturer_pn, self.attributes)

	def show(self):
		''' A simple print method. '''
		print '============================'
		print 'Name: ', self.name, type(self.name)
		print 'Project name: ', self.project.name, type(self.project)
		print 'Value: ', self.value, type(self.value)
		print 'Device: ', self.device, type(self.device)
		print 'Package: ', self.package, type(self.package)
		print 'Description: ', self.description, type(self.description)
		if self.product is not None:
			print 'Product PN: ', self.product.manufacturer_pn, type(self.product.manufacturer_pn)
		print 'Attributes: '
		for attrib in self.attributes.items():
			print attrib[0], ': ', attrib[1]
		print '============================'
		
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
	
	def part_query_constructor(self, wspace_scope):
		''' Helper method to construct the SQL queries for find_similar_parts.
		If wspace_scope == False, queries within the project scope.
		If wspace_scope == True, queries other projects in the workspace. 
		Returns a pair: The query string and the parameters tuple. '''
		
		if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
			print 'Entering %s.%s.part_query_constructor' % (self.project.name, self.name)
		
		def project_attribute_expr(attrib_name, attrib_value, name_param_number, value_param_number):
			''' Generates an SQL expression to match a single attribute for the project query. '''
			
			# self.name is always ?1, self.project.name is always ?2
			name_expr = '?%s IN (SELECT name FROM part_attributes WHERE part!=?1 AND project=?2)' % name_param_number
			value_expr = '?%s IN (SELECT value FROM part_attributes WHERE part!=?1 AND project=?2 AND name=?%s)' % (value_param_number, name_param_number)
			return '(' + name_expr + ' AND ' + value_expr + ')'
		
		def workspace_attribute_expr(attrib_name, attrib_value, name_param_number, value_param_number):
			''' Generates an SQL expression to match a single attribute for the workspace query. '''
			
			# self.name is always ?1, self.project.name is always ?2
			name_expr = '?%s IN (SELECT name FROM part_attributes WHERE project!=?2)' % name_param_number
			value_expr = '?%s IN (SELECT value FROM part_attributes WHERE project=!?2 AND name=?%s)' % (value_param_number, name_param_number)
			return '(' + name_expr + ' AND ' + value_expr + ')'
		
		if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
			print '%s.%s.part_query_constructor got past function defines OK' % (self.project.name, self.name)
		
		params_dict = {1 : self.name, 2 : self.project.name, 3 : self.value, 4 : self.device, 5 : self.package}
		if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
			print '%s.%s.part_query_constructor declared params_dict OK' % (self.project.name, self.name)
		if len(self.attributes.keys()) > 0:
			if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
				print 'Part has attributes to check'
			attribute_exprs = []
			for attr in self.attributes.items():
				greatest_param = max(params_dict.keys())
				name_key = greatest_param + 1
				val_key = greatest_param + 2
				params_dict[name_key] = attr[0]
				params_dict[val_key] = attr[1]
				if wspace_scope == True:
					attribute_exprs.append(workspace_attribute_expr(attr[0], attr[1], name_key, val_key))
				else:
					attribute_exprs.append(project_attribute_expr(attr[0], attr[1], name_key, val_key))
			
			full_attribs_expr = ' AND ' + ' AND '.join(attribute_exprs)
		else:
			if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
				print 'Part does not have attributes to check'
			full_attribs_expr = ''
			
		if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
			print '%s.%s.part_query_constructor set full_attribs_expr: ' % (self.project.name, self.name)
			print full_attribs_expr
		
		if wspace_scope == True:
			if len(full_attribs_expr) > 0:
				attributes_clause = 'SELECT DISTINCT part FROM part_attributes WHERE project!=?2' + full_attribs_expr
				query = 'SELECT * FROM parts WHERE value=?3 AND device=?4 AND package=?5 AND project!=?2 AND name IN (%s)' % attributes_clause
			else:
				query = 'SELECT * FROM parts WHERE value=?3 AND device=?4 AND package=?5 AND project!=?2'
		else:
			if len(full_attribs_expr) > 0:
				attributes_clause = 'SELECT DISTINCT part FROM part_attributes WHERE part!=?1 AND project=?2' + full_attribs_expr
				query = 'SELECT * FROM parts WHERE value=?3 AND device=?4 AND package=?5 AND project=?2 AND name IN (%s)' % attributes_clause
			else:
				query = 'SELECT * FROM parts WHERE value=?3 AND device=?4 AND package=?5 AND project=?2'
		
		if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
			print '%s.%s.part_query_constructor set query: ' % (self.project.name, self.name)
			print query
		# Make the params tuple to pass to the cursor 
		params = []
		if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
			print '%s.%s.part_query_constructor declared params tuple OK' % (self.project.name, self.name)
		for key in sorted(params_dict.keys()):
			params.append(params_dict[key])
		
		if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
			print '%s.%s.part_query_constructor returning' % (self.project.name, self.name)
			print 'Query: ', query
			print 'Parameters: ', params
			
		return query, tuple(params)
	
	def find_similar_parts(self, wspace, check_wspace=True, connection=None):
		''' Search the project and optionally workspace for parts of matching value/device/package/attributes.
		If check_wspace = True, returns a pair of lists: (project_results, workspace_results).
		If check_wspace = False, only returns the project_results list. 
		This allows for parts in different projects that incidentally have the same name to be added.
		Only returns parts that have all of the non-empty attributes in self.attributes
		(with equal values). This behavior is equivalent to self.equals(some_part, False). '''
		if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
			print 'Entering %s.%s.find_similar_parts' % (self.project.name, self.name)
		project_results = []
		workspace_results = []
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			project_query, project_params = self.part_query_constructor(False)
			cur.execute(project_query, project_params)
			rows = cur.fetchall()
			for row in rows:
				part = Part.new_from_row(row, wspace, con)
				if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
					print 'Project query found part: ', part
				project_results.append(part)
					
			if check_wspace:
				if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
					print 'checking workspace'
				
				workspace_query, workspace_params = self.part_query_constructor(True)
				cur.execute(workspace_query, workspace_params)
				rows = cur.fetchall()
				for row in rows:
					part = Part.new_from_row(row, wspace, con)
					if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
						print 'Workspace query found part: ', part
					workspace_results.append(part)
							
		finally:
			cur.close()
			if connection is None:
				con.close()
			if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
				print 'Project results list: '
				for p in project_results:
					print p
				print 'Workspace results list: '
				for p in workspace_results:
					print p
			if check_wspace:
				return (project_results, workspace_results)
			else:
				return (project_results, [])
	
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
		if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
			print 'Entering %s.%s.product_updater' % (self.project.name, self.name)
		unset_pn = ('', 'NULL', 'none', None, [])
		if(self.is_in_db(wspace, connection)):
			if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
				print "Part of same name already in DB"
			old_part = Part.select_by_name(self.name, wspace, self.project.name, connection)[0]
			#old_part.show()
			
			if self.equals(old_part, True, True, True, False):
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
						if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
							print 'first find_similar_parts call'
							print 'candidate_proj_parts: ' 
							for p in candidate_proj_parts:
								print p
							print 'candidate_wspace_parts: '
							for p in candidate_wspace_parts:
								print p
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
						
			else:	# Value/device/package/attribs mismatch
				if self.product is not None and self.product.manufacturer_pn not in unset_pn:
					self.update(wspace, connection)
				elif self.product is None or self.product.manufacturer_pn in unset_pn:
					(candidate_proj_parts, candidate_wspace_parts) = self.find_similar_parts(wspace, check_wspace, connection)
					if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
						print 'second find_similar_parts call'
						print 'candidate_proj_parts: ' 
						for p in candidate_proj_parts:
							print p
						print 'candidate_wspace_parts: '
						for p in candidate_wspace_parts:
							print p
					candidate_products = self.find_matching_products(wspace, candidate_proj_parts, candidate_wspace_parts, connection)
					if len(candidate_products) == 0:
						if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
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
			if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
				print 'Part not in DB'
			if self.product is None or self.product.manufacturer_pn in unset_pn:
				(candidate_proj_parts, candidate_wspace_parts) = self.find_similar_parts(wspace, check_wspace, connection)
				if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
					print 'third find_similar_parts call'
					print 'candidate_proj_parts: ' 
					for p in candidate_proj_parts:
						print p
					print 'candidate_wspace_parts: '
					for p in candidate_wspace_parts:
						print p
				candidate_products = self.find_matching_products(wspace, candidate_proj_parts, candidate_wspace_parts, connection)
				if len(candidate_products) == 0:
					if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
						print 'No matching products found, inserting as-is'#, self.show()
					pass
				elif len(candidate_products) == 1:
					self.product = candidate_products[0]
					if self.name == 'C58' or self.name == 'C63' or (self.project.name == 'test2' and self.name == 'C5'): # debug
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
		if self.name == 'C58' or self.name == 'C63': # debug
			print 'Entered %s.%s.fetch_attributes()' % (self.project.name, self.name)
			print 'Old self.attributes: ', self.attributes
		self.attributes.clear()
		if self.name == 'C58' or self.name == 'C63': # debug
			print 'Cleared self.attributes: ', self.attributes
		try:
			if connection is None:
				(con, cur) = wspace.con_cursor()
			else:
				con = connection
				cur = con.cursor()
			
			params = (self.name, self.project.name,)
			#cur.execute('''SELECT name, value FROM part_attributes WHERE part=? INTERSECT 
			#SELECT name, value FROM part_attributes WHERE project=?''', params)
			#if self.name == 'C58' or self.name == 'C63': # debug
			#	print '%s.fetch_attributes executing query' % self.name
			cur.execute('SELECT name, value FROM part_attributes WHERE part=? AND project=?', params)
			#if self.name == 'C58' or self.name == 'C63': # debug
			#	print '%s.fetch_attributes executed query OK' % self.name
			for row in cur.fetchall():
				if self.name == 'C58' or self.name == 'C63': # debug
					print '%s.fetch_attributes found row: %s' % (self.name, row)
				self.attributes[row[0]] = row[1]
			if self.name == 'C58' or self.name == 'C63': # debug
				print 'New self.attributes: ', self.attributes
			
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
		# TODO: This does not remove any old attribs from the DB that are not in self.attributes
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
			if self.name == 'C58' or self.name == 'C63': # debug
				print 'self.attributes', self.attributes
				print 'db_attribs: ', db_attribs
				print 'old_attribs: ', old_attribs
				print 'new_attribs: ', new_attribs
			cur.executemany('INSERT OR REPLACE INTO part_attributes VALUES (NULL,?,?,?,?)', new_attribs)
			cur.executemany('UPDATE part_attributes SET value=? WHERE part=? AND project=? AND name=?', old_attribs)
		
		finally:
			cur.close()
			if connection is None:
				con.close()
