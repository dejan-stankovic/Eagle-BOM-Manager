import csv
import pygtk
pygtk.require('2.0')
import gtk
import y_serial_v060 as y_serial
import shutil
import os
import sqlite3
import types
from urbm_product import Product
from urbm_bompart import bomPart
from urbm_bom import BOM
import gobject

urbmDB = y_serial.Main(os.path.join(os.getcwd(), "urbm.sqlite"))
urbmDB.createtable('products')
activeProjectName = 'test1'
inputFile = os.path.join(os.getcwd(), "test.csv")	# TODO: Test dummy

#active_bom = BOM("test1", 'Test BOM 1', urbmDB, os.path.join(os.getcwd(), "test.csv"))

def getProductDBSize():
	dict = urbmDB.selectdic("?", 'products')

''' Returns a list of BOM project tables in the DB. '''
def listProjects():
	conn = sqlite3.connect("urbm.sqlite")
	cur = conn.cursor()
	projects = []
	a = "SELECT name FROM sqlite_master"
	b = "WHERE type='table' AND name IS NOT 'products' OR 'dummy'"
	c = "ORDER BY name"
	sql = ' '.join( [a, b, c] )
	cur.execute(sql)
	answer = cur.fetchall()
	cur.close()
	conn.close()
	for p in answer:
		projects.append(p[0])
	return projects

'''Main GUI class'''
class URBM(gobject.GObject):
	''' Query the database for all project tables.'''
	
	def delete_event(self, widget, event, data=None):
		print "delete event occurred"
		return False
		
	def destroy(self, widget, data=None):
		gtk.main_quit()

	# -------- CALLBACK METHODS --------
	''' Callback for the input file Open dialog in the New Project dialog. '''
	def newProjectInputFileCallback(self, widget, data=None):
		self.inputFileDialog.run()
		self.inputFileDialog.hide()
		self.newProjectInputFileEntry.set_text(self.inputFileDialog.get_filename())
	
	'''Callback for the New Project button. '''
	def projectNewCallback(self, widget, data=None):
		response = self.newProjectDialog.run()
		self.newProjectDialog.hide()
		newName = self.newProjectNameEntry.get_text()
		curProjects = listProjects()
		if newName in curProjects:
			print 'Error: Name in use!'
			self.projectNameTakenDialog.run()
			self.projectNameTakenDialog.hide()
		elif response == gtk.RESPONSE_ACCEPT: 
			# Create project
			print 'Creating new project'
			new = BOM(newName, self.newProjectDescriptionEntry.get_text(), urbmDB, self.newProjectInputFileEntry.get_text())
			new.writeToDB()
			self.projectStorePopulate()
		self.newProjectNameEntry.set_text('')
		self.newProjectDescriptionEntry.set_text('')
		#self.newProjectDatabaseFileEntry.set_text('')
		self.newProjectInputFileEntry.set_text('')
	
	'''Callback for the "Read CSV" button on the BOM tab.'''
	def readInputCallback(self, widget, data=None):
		self.active_bom.readFromFile()
		#Read back last entry
		urbmDB.view(1, self.active_bom.name)
		if self.bomGroupName.get_active():
			self.bomStorePopulateByName()
		elif self.bomGroupValue.get_active():
			self.bomStorePopulateByValue()
		elif self.bomGroupPN.get_active():
			self.bomStorePopulateByPN()
		self.window.show_all()
	
	'''Callback for the "Read DB" button on the BOM tab.'''
	def bomReadDBCallback(self, widget, data=None):
		print "Read DB callback"
		self.active_bom = BOM.readFromDB(urbmDB, activeProjectName)
		if self.bomGroupName.get_active():
			self.bomStorePopulateByName()
		elif self.bomGroupValue.get_active():
			self.bomStorePopulateByVal()
		elif self.bomGroupPN.get_active():
			self.bomStorePopulateByPN()
		self.window.show_all()
	
	'''Callback method triggered when a BOM line item is selected.'''
	def bomSelectionCallback(self, widget, data=None):
		# Set class fields for currently selected item
		(model, rowIter) = self.bomTreeView.get_selection().get_selected()
		#print 'rowIter is: ', rowIter, '\n'
		#print 'model.get(rowIter,0)[0] is: ', model.get(rowIter,0)[0]
		self.selectedBomPart = urbmDB.select(model.get(rowIter,0)[0], self.active_bom.name)
		# Grab the vendor part number for the selected item from the label text
		selectedPN = model.get(rowIter,5)[0]
		print "selectedPN is: %s" % selectedPN
		if selectedPN != "none": # Look up part in DB
			# Set class field for currently selected product
			print "Querying with selectedPN: %s" % selectedPN
			self.bomSelectedProduct.vendor_pn = selectedPN
			
			self.bomSelectedProduct.selectOrScrape()
			self.setPartInfoLabels(self.bomSelectedProduct)
			self.setPartPriceLabels(self.bomSelectedProduct)
		else:
			self.destroyPartPriceLabels()
			self.clearPartInfoLabels()
	
	'''Callback method activated by the BOM grouping radio buttons.
	Redraws the BOM TreeView with the approporiate goruping for the selected radio.'''
	def bomGroupCallback(self, widget, data=None):
		#print "%s was toggled %s" % (data, ("OFF", "ON")[widget.get_active()])
		
		# Figure out which button is now selected
		if widget.get_active():
			if 'name' in data:
				self.bomStorePopulateByName()
				
			elif 'value' in data:
				self.bomStorePopulateByVal()
					
			elif 'product' in data:
				self.bomStorePopulateByPN()
					
			self.window.show_all()
	
	'''Callback method activated by clicking a BOM column header.
	Sorts the BOM TreeView by the values in the clicked column.'''
	def bomSortCallback(self, widget):
		print widget.get_sort_order()
		widget.set_sort_column_id(0)
		# TODO: On sorting by a different column, the indicator does not go away
		# This may be because with the current test set, the other columns are still technically sorted
	
	'''Callback method for the "Edit Part" button in the BOM tab.
	Opens a dialog window with form fields for each BOM Part object field.'''
	def bomEditPartCallback(self, widget, data=None):
		# Open a text input prompt window
		editPartDialog = gtk.Dialog("Edit part", self.window, 
						gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
						(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, 
						gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
		
		# -------- DECLARATIONS --------
		# Field labels
		editPartNameLabel = gtk.Label("Name: ")
		editPartValueLabel = gtk.Label("Value: ")
		editPartDeviceLabel = gtk.Label("Device: ")
		editPartPackageLabel = gtk.Label("Package: ")
		editPartDescriptionLabel = gtk.Label("Description: ")
		editPartVendorLabel = gtk.Label("Vendor: ")
		editPartVendorPNLabel = gtk.Label("Vendor Part Number: ")
		
		# Field entry elements
		self.editPartNameEntry = gtk.Entry()
		self.editPartValueEntry = gtk.Entry()
		self.editPartDeviceEntry = gtk.Entry()
		self.editPartPackageEntry = gtk.Entry()
		self.editPartDescriptionEntry = gtk.Entry()
		self.editPartProductEntry = gtk.Entry()
		
		editPartVendorCombo = gtk.combo_box_new_text()
		editPartVendorCombo.append_text(Product.VENDOR_DK)
		editPartVendorCombo.append_text(Product.VENDOR_FAR)
		editPartVendorCombo.append_text(Product.VENDOR_FUE)
		editPartVendorCombo.append_text(Product.VENDOR_JAM)
		editPartVendorCombo.append_text(Product.VENDOR_ME)
		editPartVendorCombo.append_text(Product.VENDOR_NEW)
		editPartVendorCombo.append_text(Product.VENDOR_SFE)
		
		# Return values
		self.productEntryText = ""
		
		# HBoxes
		editPartDialogNameHBox = gtk.HBox()
		editPartDialogValueHBox = gtk.HBox()
		editPartDialogDeviceHBox = gtk.HBox()
		editPartDialogPackageHBox = gtk.HBox()
		editPartDialogDescriptionHBox = gtk.HBox()
		editPartDialogVendorHBox = gtk.HBox()
		editPartDialogVendorPNHBox = gtk.HBox()
		
		# -------- CONFIGURATION --------
		# Label alignment
		editPartNameLabel.set_alignment(0.0, 0.5)
		editPartValueLabel.set_alignment(0.0, 0.5)
		editPartDeviceLabel.set_alignment(0.0, 0.5)
		editPartPackageLabel.set_alignment(0.0, 0.5)
		editPartDescriptionLabel.set_alignment(0.0, 0.5)
		editPartVendorLabel.set_alignment(0.0, 0.5)
		editPartVendorPNLabel.set_alignment(0.0, 0.5)
		
		# Set default text of entry fields to current part values
		self.editPartNameEntry.set_text(self.selectedBomPart.name)
		self.editPartValueEntry.set_text(self.selectedBomPart.value)
		self.editPartDeviceEntry.set_text(self.selectedBomPart.device)
		self.editPartPackageEntry.set_text(self.selectedBomPart.package)
		self.editPartDescriptionEntry.set_text(self.selectedBomPart.description)
		self.editPartProductEntry.set_text(self.selectedBomPart.product)
		
		# Pack labels/entry fields into HBoxes
		editPartDialogNameHBox.pack_start(editPartNameLabel, False, True, 0)
		editPartDialogNameHBox.pack_end(self.editPartNameEntry, False, True, 0)
		
		editPartDialogValueHBox.pack_start(editPartValueLabel, False, True, 0)
		editPartDialogValueHBox.pack_end(self.editPartValueEntry, False, True, 0)
		
		editPartDialogDeviceHBox.pack_start(editPartDeviceLabel, False, True, 0)
		editPartDialogDeviceHBox.pack_end(self.editPartDeviceEntry, False, True, 0)
		
		editPartDialogPackageHBox.pack_start(editPartPackageLabel, False, True, 0)
		editPartDialogPackageHBox.pack_end(self.editPartPackageEntry, False, True, 0)
		
		editPartDialogDescriptionHBox.pack_start(editPartDescriptionLabel, False, True, 0)
		editPartDialogDescriptionHBox.pack_end(self.editPartDescriptionEntry, False, True, 0)
		
		editPartDialogVendorHBox.pack_start(editPartVendorLabel, True, True, 0)
		editPartDialogVendorHBox.pack_end(editPartVendorCombo, True, True, 0)
		
		editPartDialogVendorPNHBox.pack_start(editPartVendorPNLabel, True, True, 0)
		editPartDialogVendorPNHBox.pack_end(self.editPartProductEntry, gtk.RESPONSE_ACCEPT)
		
		# Pack HBoxes into vbox
		editPartDialog.vbox.set_spacing(1)
		editPartDialog.vbox.pack_start(editPartDialogNameHBox, True, True, 0)
		editPartDialog.vbox.pack_start(editPartDialogValueHBox, True, True, 0)
		editPartDialog.vbox.pack_start(editPartDialogDeviceHBox, True, True, 0)
		editPartDialog.vbox.pack_start(editPartDialogPackageHBox, True, True, 0)
		editPartDialog.vbox.pack_start(editPartDialogDescriptionHBox, True, True, 0)
		editPartDialog.vbox.pack_start(editPartDialogVendorHBox, True, True, 0)
		editPartDialog.vbox.pack_start(editPartDialogVendorPNHBox, True, True, 0)
		
		# Show everything
		editPartDialog.vbox.show_all()
		response = editPartDialog.run()
		editPartDialog.hide()
		
		if response == gtk.RESPONSE_ACCEPT:
			# If the product text entry field is left blank, set the product to "none"
			if type(self.editPartProductEntry.get_text()) is types.NoneType or len(self.editPartProductEntry.get_text()) == 0:
				self.productEntryText = "none"
			else:
				self.productEntryText = self.editPartProductEntry.get_text()
			
			# Set selectedBomPart
			# TODO: If grouping by value or PN, what to do? Grey out the name field?
			# It should write the rest to ALL of the parts in the row
			self.selectedBomPart.name = self.editPartNameEntry.get_text()
			self.selectedBomPart.value = self.editPartValueEntry.get_text()
			self.selectedBomPart.device = self.editPartDeviceEntry.get_text()
			self.selectedBomPart.package = self.editPartPackageEntry.get_text()
			self.selectedBomPart.description = self.editPartDescriptionEntry.get_text()
			print "Setting selectedBomPart.product to: %s" % self.editPartProductEntry.get_text()
			self.selectedBomPart.product = self.productEntryText
			print "selectedBomPart's product field: %s" % self.selectedBomPart.product
			
			# Make sure the user selected a vendor
			# If not, default to Digikey for now
			# TODO: If a product was previously set, default to the current vendor
			# TODO: Can this be a "required field" that will prevent the OK button 
			# from working (greyed out) if a part number is also entered?
			if type(editPartVendorCombo.get_active_text()) is types.NoneType:
				print "NoneType caught"
				self.bomSelectedProduct.vendor = Product.VENDOR_DK
			else:	
				self.bomSelectedProduct.vendor = editPartVendorCombo.get_active_text()
			
			self.selectedBomPart.writeToDB()
			self.active_bom.updateParts(self.selectedBomPart)
			
			if self.bomGroupName.get_active():
				self.bomStorePopulateByName()
			elif self.bomGroupValue.get_active():
				self.bomStorePopulateByVal()
			elif self.bomGroupPN.get_active():
				self.bomStorePopulateByPN()
					
			self.bomSelectedProduct.vendor_pn = self.productEntryText
			self.bomSelectedProduct.selectOrScrape()
			if self.bomSelectedProduct.vendor_pn == "none":
				self.clearPartInfoLabels()
				self.destroyPartPriceLabels()
			else:
				self.setPartInfoLabels(self.bomSelectedProduct)
				self.setPartPriceLabels(self.bomSelectedProduct)
	
	'''Callback for the "Read DB" button on the product DB tab.'''
	def dbReadDBCallback(self, widget, data=None):
		print "Read DB callback"
		#prodsDict = urbmDB.selectdic(Product.PROD_SEL_ALL, "products")
		prodsDict = urbmDB.selectdic("*", "products")
		self.dbDraw(prodsDict)
		self.window.show_all()
	
	'''Callback method triggered when a product DB item is selected.'''
	def dbRadioCallback(self, widget, data=None):
		print "dbRadioCallback"
		# Set class fields for currently selected item
		self.dbSelectedRow = int(data) 	# Convert str to int
		# Grab the vendor part number for the selected item from the label text
		selectedPN = self.dbContentLabels[self.dbSelectedRow][1].get_text()
		self.dbSelectedProduct = urbmDB.select(selectedPN, "products")
	 
	# -------- HELPER METHODS --------
	def projectStorePopulate(self):
		self.projectStore.clear()
		# Columns: Name, Description, Database, Input File
		projectsList = listProjects()
		for p in projectsList:
			if p != 'dummy':
				bom = BOM.readFromDB(urbmDB, p)
				iter = self.projectStore.append([bom.name, bom.description, urbmDB.db, bom.input])
	
	''' Clear self.bomStore and repopulate it, grouped by name. '''
	def bomStorePopulateByName(self):
		self.bomStore.clear()
		for p in self.active_bom.parts:
			temp = urbmDB.select(p[0], self.active_bom.name)
			iter = self.bomStore.append([temp.name, temp.value, temp.device, temp.package, temp.description, temp.product, 1])
	
	''' Clear self.bomStore and repopulate it, grouped by value. '''
	def bomStorePopulateByVal(self):
		self.bomStore.clear()
		self.active_bom.sortByVal()
		self.active_bom.setValCounts()
		
		for val in self.active_bom.valCounts.keys():
			groupName = "\t"	# Clear groupName and prepend a tab
			# TODO: Does this split up parts of the same value but different package?
			# If not, the "part number" column will be bad
			group = urbmDB.selectdic("#val=" + val, self.active_bom.name)
			for part in group.values():
				groupName += part[2].name + ", "
			
			# Replace trailing comma with tab
			groupName = groupName[0:-2]
			temp = group[group.keys()[0]][2]	# Part object
			iter = self.bomStore.append([groupName, temp.value, temp.device, temp.package, temp.description, temp.product, self.active_bom.valCounts[val]])
	
	''' Clear self.bomStore and repopulate it, grouped by part number. '''		
	def bomStorePopulateByPN(self):
		self.bomStore.clear()
		self.active_bom.sortByProd()
		self.active_bom.setProdCounts()
		
		for prod in self.active_bom.prodCounts.keys():
			groupName = "\t"	# Clear groupName and prepend a tab
			print "Querying with prod =", prod, " of length ", len(prod)
			# Catch empty product string
			if prod == ' ' or len(prod) == 0: 
				print "Caught empty product"
				group = urbmDB.selectdic("#prod=none", self.active_bom.name)
			else:
				group = urbmDB.selectdic("#prod=" + prod, self.active_bom.name)
			print "Group: \n", group
			for part in group.values():	# TODO: Ensure this data is what we expect
				groupName += part[2].name + ", "
			
			# Replace trailing comma with tab
			groupName = groupName[0:-2]
			
			temp = group[group.keys()[0]][2]	# Part object
			iter = self.bomStore.append([groupName, temp.value, temp.device, temp.package, temp.description, temp.product, self.active_bom.prodCounts[prod]])
	
	'''Set the Part Information pane fields based on the fields of a given 
	product object.'''		
	def setPartInfoLabels(self, prod):
		self.partInfoVendorLabel2.set_text(prod.vendor)
		self.partInfoVendorPNLabel2.set_text(prod.vendor_pn)
		self.partInfoInventoryLabel2.set_text(str(prod.inventory))
		self.partInfoManufacturerLabel2.set_text(prod.manufacturer)
		self.partInfoManufacturerPNLabel2.set_text(prod.mfg_pn)
		self.partInfoDescriptionLabel2.set_text(prod.description)
		self.partInfoDatasheetLabel2.set_text(prod.datasheet)
		self.partInfoCategoryLabel2.set_text(prod.category)
		self.partInfoFamilyLabel2.set_text(prod.family)
		self.partInfoSeriesLabel2.set_text(prod.series)
		self.partInfoPackageLabel2.set_text(prod.package)

	'''Clears the Part Information pane fields, setting the text of each Label
	object to a tab character.'''
	def clearPartInfoLabels(self):
		self.partInfoVendorLabel2.set_text("\t")
		self.partInfoVendorPNLabel2.set_text("\t")
		self.partInfoInventoryLabel2.set_text("\t")
		self.partInfoManufacturerLabel2.set_text("\t")
		self.partInfoManufacturerPNLabel2.set_text("\t")
		self.partInfoDescriptionLabel2.set_text("\t")
		self.partInfoDatasheetLabel2.set_text("\t")
		self.partInfoCategoryLabel2.set_text("\t")
		self.partInfoFamilyLabel2.set_text("\t")
		self.partInfoSeriesLabel2.set_text("\t")
		self.partInfoPackageLabel2.set_text("\t")
	
	def destroyPartPriceLabels(self):
		for r in self.priceBreakLabels:
			r.destroy()
			
		for r in self.unitPriceLabels:
			r.destroy()
			
		for r in self.extPriceLabels:
			r.destroy()
		
	def setPartPriceLabels(self, prod):
		n = len(prod.prices)
		print "n =", n
		k = sorted(prod.prices.keys())
		print "prod.prices = \n", prod.prices
		print "sorted(prod.prices.keys()) = \n", k
		self.partInfoPricingTable.resize(n+1, 3)
		self.destroyPartPriceLabels()
		
		self.priceBreakLabels.append(gtk.Label("Price Break"))
		self.unitPriceLabels.append(gtk.Label("Unit Price"))
		self.extPriceLabels.append(gtk.Label("Extended Price"))
		
		self.partInfoPricingTable.attach(self.priceBreakLabels[0],  0, 1, 0, 1)
		self.partInfoPricingTable.attach(self.unitPriceLabels[0],  1, 2, 0, 1)
		self.partInfoPricingTable.attach(self.extPriceLabels[0],  2, 3, 0, 1)
		
		rowNum = 1
		for i in range(n):
			#k[i] is a key of prod.prices()
			self.priceBreakLabels.append(gtk.Label(str(k[i]) + '   '))
			self.priceBreakLabels[rowNum].set_alignment(0.5, 0.5)
			self.unitPriceLabels.append(gtk.Label(str(prod.prices[k[i]]) + '   '))
			self.unitPriceLabels[rowNum].set_alignment(1.0, 0.5)
			self.extPriceLabels.append(gtk.Label(str( k[i] *  prod.prices[k[i]]) + '   '))
			self.extPriceLabels[rowNum].set_alignment(1.0, 0.5)
			
			self.partInfoPricingTable.attach(self.priceBreakLabels[rowNum],  0, 1, rowNum, rowNum+1)
			self.partInfoPricingTable.attach(self.unitPriceLabels[rowNum],  1, 2, rowNum, rowNum+1)
			self.partInfoPricingTable.attach(self.extPriceLabels[rowNum],  2, 3, rowNum, rowNum+1)
			rowNum += 1
			
		self.window.show_all()
		
	def dbTableHeaders(self):
		self.dbTable.attach(self.dbVendorLabel, 0, 1, 0, 1)
		self.dbTable.attach(self.dbVendorPNLabel, 1, 2, 0, 1)
		self.dbTable.attach(self.dbInventoryLabel, 2, 3, 0, 1)
		self.dbTable.attach(self.dbManufacturerLabel, 3, 4, 0, 1)
		self.dbTable.attach(self.dbManufacturerPNLabel, 4, 5, 0, 1)
		self.dbTable.attach(self.dbDescriptionLabel, 5, 6, 0, 1)
		self.dbTable.attach(self.dbDatasheetLabel, 6, 7, 0, 1)
		self.dbTable.attach(self.dbCategoryLabel, 7, 8, 0, 1)
		self.dbTable.attach(self.dbFamilyLabel, 8, 9, 0, 1)
		self.dbTable.attach(self.dbSeriesLabel, 9, 10, 0, 1)
		self.dbTable.attach(self.dbPackageLabel, 10, 11, 0, 1)
	
	'''Create Label instances for a given number of Product DB rows.'''	
	def dbCreateLabels(self, numRows):
		rows = []
		for x in range(numRows):
			row = []
			for i in range(11):
				row.append(gtk.Label(None))
			rows.append(row)
		
		return rows
	
	'''Destroy current self.dbContentLabels Label instances.''' 
	def dbDestroyLabels(self):
		for x in self.dbContentLabels:
			for y in x:
				y.destroy()
				
	'''Create RadioButton instances for a given number of Product DB rows.'''
	def dbCreateRadios(self, numRows):
		radios = []
		for x in range(numRows):
			radios.append(gtk.RadioButton(self.dbRadioGroup))
			radios[x].connect("toggled", self.dbRadioCallback, str(x))
		return radios
	
	def dbAttachRadios(self):
		r = 0
		for radio in self.dbRadios:
			self.dbTable.attach(radio,  0, 11, r+1, r+2)
			r += 1
	
	def dbDestroyRadios(self):
		for r in self.dbRadios:
			r.destroy()
	
	''' @param row considers index 0 to be the first row of content after headers'''
	def dbPopulateRow(self, product, row):
		self.dbContentLabels[row][0].set_label("\t" + product.vendor)
		self.dbContentLabels[row][1].set_label(product.vendor_pn)
		self.dbContentLabels[row][2].set_label(str(product.inventory))
		self.dbContentLabels[row][3].set_label(product.manufacturer)
		self.dbContentLabels[row][4].set_label(product.mfg_pn)
		self.dbContentLabels[row][5].set_label(product.description)
		self.dbContentLabels[row][6].set_label(product.datasheet)
		self.dbContentLabels[row][7].set_label(product.category)
		self.dbContentLabels[row][8].set_label(product.family)
		self.dbContentLabels[row][9].set_label(product.series)
		self.dbContentLabels[row][10].set_label(product.package)
		
	def dbAttachRow(self, row):
		i = 0
		for label in self.dbContentLabels[row]:
			self.dbTable.attach(label,  i, i+1, row+1, row+2)
			i += 1
	
	''' @param d Dictionary containing the contents of the "products" table.'''
	def dbDraw(self, d):
		nr = len(d)	# numRows
		old = len(self.dbContentLabels)
		self.dbDestroyLabels()
		self.dbDestroyRadios()
		del self.dbContentLabels[0:old]
		del self.dbRadios[0:old]
		
		self.dbTable.resize(nr+1, 12)
		self.dbContentLabels = self.dbCreateLabels(nr)
		self.dbRadios = self.dbCreateRadios(nr)
		self.dbAttachRadios()
		
		rowNum = 0
		for p in d.values():
			# p[2] is a Product object from the DB
			self.dbPopulateRow(p[2], rowNum)
			self.dbAttachRow(rowNum)
			rowNum += 1
			
		self.window.show_all()
		
	def __init__(self):
		# -------- DECLARATIONS --------
		self.active_bom = BOM('dummy', 'Active BOM Declaration', urbmDB, inputFile)
		
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.mainBox = gtk.VBox(False, 0)
		self.menuBar = gtk.MenuBar()
		self.notebook = gtk.Notebook()
		self.projectTabLabel = gtk.Label("Projects")
		self.bomTabLabel = gtk.Label("BOM Editor")
		self.dbTabLabel = gtk.Label("Product Database")
		
		# --- Projects tab ---
		self.projectBox = gtk.VBox(False, 0) # First tab in notebook
		self.projectToolbar = gtk.Toolbar()
		self.projectNewButton = gtk.ToolButton(None, "New Project")
		self.projectOpenButton = gtk.ToolButton(None, "Open Project")
		self.projectEditButton = gtk.ToolButton(None, "Edit Project")
		self.projectDeleteButton = gtk.ToolButton(None, "Delete Project")
		self.projectFrame = gtk.Frame("Projects") 
		self.projectScrollWin = gtk.ScrolledWindow()
		
		# New Project menu
		self.newProjectDialog = gtk.Dialog('New Project', self.window, 
										gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, 
										(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
		
		self.newProjectNameHBox = gtk.HBox()
		self.newProjectDescriptionHBox = gtk.HBox()
		#newProjectDatabaseFileHBox = gtk.HBox()
		self.newProjectInputFileHBox = gtk.HBox()
		
		self.newProjectNameLabel = gtk.Label("Name: ")
		self.newProjectDescriptionLabel = gtk.Label("Description: ")
		#self.newProjectDatabaseFileLabel = gtk.Label("Database file: ")
		self.newProjectInputFileLabel = gtk.Label("Input file: ")
		
		self.newProjectNameEntry = gtk.Entry()
		self.newProjectDescriptionEntry = gtk.Entry()
		# TODO: Add a database file Entry/FileDialog when adding multiple DB file support
		self.newProjectInputFileButton = gtk.Button('Browse', gtk.STOCK_OPEN)
		self.newProjectInputFileEntry = gtk.Entry()
		self.inputFileDialog = gtk.FileChooserDialog('Select Input File', 
													self.newProjectDialog, gtk.FILE_CHOOSER_ACTION_OPEN, 
													(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
		
		self.projectNameTakenDialog = gtk.MessageDialog(self.newProjectDialog, 
												gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, 
												gtk.BUTTONS_OK, 'Error: Project name in use. \nPlease select a different name.')
		
		# Projects list
		# Columns: Name, Description, Database, Input File
		self.projectStore = gtk.ListStore(str, str, str, str)
		self.projectNameCell = gtk.CellRendererText()
		self.projectNameColumn = gtk.TreeViewColumn('Name', self.projectNameCell)
		self.projectDescriptionCell = gtk.CellRendererText()
		self.projectDescriptionColumn = gtk.TreeViewColumn('Description', self.projectDescriptionCell)
		self.projectDBFileCell = gtk.CellRendererText()
		self.projectDBFileColumn = gtk.TreeViewColumn('Database File', self.projectDBFileCell)
		self.projectInputFileCell = gtk.CellRendererText()
		self.projectInputFileColumn = gtk.TreeViewColumn('Input File', self.projectInputFileCell)
		self.projectTreeView = gtk.TreeView() # Associate with self.projectStore later, not yet!
		
		# --- BOM tab ---
		self.bomTabBox = gtk.VBox(False, 0) # Second tab in notebook
		self.bomToolbar = gtk.Toolbar()
		self.bomReadInputButton = gtk.ToolButton(None, "Read CSV")
		self.bomReadDBButton = gtk.ToolButton(None, "Read DB")
		self.bomEditPartButton = gtk.ToolButton(None, "Edit Part")
		self.bomHPane = gtk.HPaned()	
		self.bomVPane = gtk.VPaned()	# Goes in right side of bomHPane
		
		self.bomFrame = gtk.Frame("BOM") # Goes in left side of bomHPane
		self.bomScrollBox = gtk.VBox(False, 0) # Holds bomScrollWin and bomRadioBox
		self.bomScrollWin = gtk.ScrolledWindow() # Holds bomTable
		
		# Columns: Name, Value, Device, Package, Description, MFG PN, Quantity
		self.bomStore = gtk.ListStore(str, str, str, str, str, str, int)
									
		self.bomNameCell = gtk.CellRendererText()
		self.bomNameColumn = gtk.TreeViewColumn('Name', self.bomNameCell)
		self.bomValueCell = gtk.CellRendererText()
		self.bomValueColumn = gtk.TreeViewColumn('Value', self.bomValueCell)
		self.bomDeviceCell = gtk.CellRendererText()
		self.bomDeviceColumn = gtk.TreeViewColumn('Device', self.bomDeviceCell)
		self.bomPackageCell = gtk.CellRendererText()
		self.bomPackageColumn = gtk.TreeViewColumn('Package', self.bomPackageCell)
		self.bomDescriptionCell = gtk.CellRendererText()
		self.bomDescriptionColumn = gtk.TreeViewColumn('Description', self.bomDescriptionCell)
		self.bomPNCell = gtk.CellRendererText()
		self.bomPNColumn = gtk.TreeViewColumn('Part Number', self.bomPNCell)
		self.bomQuantityCell = gtk.CellRendererText()
		self.bomQuantityColumn = gtk.TreeViewColumn('Quantity', self.bomQuantityCell)
		
		self.bomTreeView = gtk.TreeView()
		
		self.bomRadioBox = gtk.HBox(False, 0)
		self.bomRadioLabel = gtk.Label("Group by:")
		self.bomGroupName = gtk.RadioButton(None, "Name")
		self.bomGroupValue = gtk.RadioButton(self.bomGroupName, "Value")
		self.bomGroupPN = gtk.RadioButton(self.bomGroupName, "Part Number")
		
		self.bomSelectedProduct = Product(Product.VENDOR_DK, "init", urbmDB)
		self.selectedBomPart = bomPart("init", "init", "init", "init", self.active_bom)
		
		self.partInfoFrame = gtk.Frame("Part information") # Goes in top half of bomVPane
		self.partInfoRowBox = gtk.VBox(False, 20) # Fill with HBoxes 
		
		self.partInfoInfoTable = gtk.Table(11, 2, False) # Vendor, PNs, inventory, etc
		self.partInfoVendorLabel1 = gtk.Label("Vendor: ")
		self.partInfoVendorLabel2 = gtk.Label(None)
		self.partInfoVendorPNLabel1 = gtk.Label("Vendor Part Number: ")
		self.partInfoVendorPNLabel2 = gtk.Label(None)
		self.partInfoInventoryLabel1 = gtk.Label("Inventory: ")
		self.partInfoInventoryLabel2 = gtk.Label(None)
		self.partInfoManufacturerLabel1 = gtk.Label("Manufacturer: ")
		self.partInfoManufacturerLabel2 = gtk.Label(None)
		self.partInfoManufacturerPNLabel1 = gtk.Label("Manufacturer Part Number: ")
		self.partInfoManufacturerPNLabel2 = gtk.Label(None)
		self.partInfoDescriptionLabel1 = gtk.Label("Description: ")
		self.partInfoDescriptionLabel2 = gtk.Label(None)
		self.partInfoDatasheetLabel1 = gtk.Label("Datasheet filename: ")
		self.partInfoDatasheetLabel2 = gtk.Label(None)
		self.partInfoCategoryLabel1 = gtk.Label("Category: ")
		self.partInfoCategoryLabel2 = gtk.Label(None)
		self.partInfoFamilyLabel1 = gtk.Label("Family: ")
		self.partInfoFamilyLabel2 = gtk.Label(None)
		self.partInfoSeriesLabel1 = gtk.Label("Series: ")
		self.partInfoSeriesLabel2 = gtk.Label(None)
		self.partInfoPackageLabel1 = gtk.Label("Package/case: ")
		self.partInfoPackageLabel2 = gtk.Label(None)
		
		self.partInfoPricingTable = gtk.Table(8, 3 , False) # Price breaks
		self.priceBreakLabels = []
		
		self.unitPriceLabels = []
		
		self.extPriceLabels = []
		
		self.partInfoButtonBox = gtk.HBox(False, 0)

		self.scrapeButton = gtk.Button("Scrape", stock=gtk.STOCK_REFRESH)
		self.partDatasheetButton = gtk.Button("Datasheet", stock=gtk.STOCK_PROPERTIES)
		
		self.pricingFrame = gtk.Frame("Project pricing") # Goes in bottom half of bomVPane
		self.orderSizeScaleAdj = gtk.Adjustment(1, 1, 10000, 1, 10, 200)
		self.orderSizeScale = gtk.HScale(self.orderSizeScaleAdj)
		self.orderSizeText = gtk.Entry(10000)
		
		# --- Product DB tab ---
		self.dbBox = gtk.VBox(False, 0) # Third tab in notebook
		self.dbToolbar = gtk.Toolbar()
		self.dbReadDBButton = gtk.ToolButton(None, "Read DB")
		self.dbFrame = gtk.Frame("Product database") 
		self.dbScrollWin = gtk.ScrolledWindow()
		self.dbTable = gtk.Table(50, 6, False)
		self.dbVendorLabel = gtk.Label("Vendor")
		self.dbVendorPNLabel = gtk.Label("Vendor Part Number")
		self.dbInventoryLabel = gtk.Label("Inventory")
		self.dbManufacturerLabel = gtk.Label("Manufacturer")
		self.dbManufacturerPNLabel = gtk.Label("Manufacturer Part Number")
		self.dbDescriptionLabel = gtk.Label("Description")
		self.dbDatasheetLabel = gtk.Label("Datasheet filename")
		self.dbCategoryLabel = gtk.Label("Category")
		self.dbFamilyLabel = gtk.Label("Family")
		self.dbSeriesLabel = gtk.Label("Series")
		self.dbPackageLabel = gtk.Label("Package/case")
		self.dbContentLabels = []
		self.dbRadioGroup = gtk.RadioButton(None)
		self.dbRadios = self.dbCreateRadios(0)
		
		# -------- CONFIGURATION --------
		self.window.set_title("Unified Robotics BOM Manager") 
		# TODO: Add project name to window title on file open
		self.window.connect("delete_event", self.delete_event)
		self.window.connect("destroy", self.destroy)
		
		self.notebook.set_tab_pos(gtk.POS_TOP)
		self.notebook.append_page(self.projectBox, self.projectTabLabel)
		self.notebook.append_page(self.bomTabBox, self.bomTabLabel)
		self.notebook.append_page(self.dbBox, self.dbTabLabel)
		self.notebook.set_show_tabs(True)
		
		# Project selection tab
		self.projectNewButton.connect("clicked", self.projectNewCallback)
		self.newProjectInputFileButton.connect("clicked", self.newProjectInputFileCallback)
		
		self.newProjectNameLabel.set_alignment(0.0, 0.5)
		self.newProjectDescriptionLabel.set_alignment(0.0, 0.5)
		#self.newProjectDatabaseFileLabel.set_alignment(0.0, 0.5)
		self.newProjectInputFileLabel.set_alignment(0.0, 0.5)
		
		self.projectScrollWin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		#self.projectTreeView.set_fixed_height_mode(True)
		self.projectTreeView.set_reorderable(True)
		self.projectTreeView.set_headers_clickable(True)
		
		self.projectNameColumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
		self.projectDescriptionColumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
		self.projectDBFileColumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
		self.projectInputFileColumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
		
		self.projectNameColumn.set_resizable(True)
		self.projectDescriptionColumn.set_resizable(True)
		self.projectDBFileColumn.set_resizable(True)
		self.projectInputFileColumn.set_resizable(True)
		
		self.projectNameColumn.set_attributes(self.projectNameCell, text=0)
		self.projectDescriptionColumn.set_attributes(self.projectDescriptionCell, text=1)
		self.projectDBFileColumn.set_attributes(self.projectDBFileCell, text=2)
		self.projectInputFileColumn.set_attributes(self.projectInputFileCell, text=3)
		
		self.projectTreeView.append_column(self.projectNameColumn)
		self.projectTreeView.append_column(self.projectDescriptionColumn)
		self.projectTreeView.append_column(self.projectDBFileColumn)
		self.projectTreeView.append_column(self.projectInputFileColumn)
		self.projectStorePopulate()
		self.projectTreeView.set_model(self.projectStore)
		
		# BOM tab
		
		self.bomNameColumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
		self.bomValueColumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
		self.bomDeviceColumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
		self.bomPackageColumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
		self.bomDescriptionColumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
		self.bomPNColumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
		self.bomQuantityColumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
		
		self.bomNameColumn.set_resizable(True)
		self.bomValueColumn.set_resizable(True)
		self.bomDeviceColumn.set_resizable(True)
		self.bomPackageColumn.set_resizable(True)
		self.bomDescriptionColumn.set_resizable(True)
		self.bomPNColumn.set_resizable(True)
		self.bomQuantityColumn.set_resizable(True)
		
		self.bomNameColumn.set_clickable(True)
		self.bomValueColumn.set_clickable(True)
		self.bomDeviceColumn.set_clickable(True)
		self.bomPackageColumn.set_clickable(True)
		self.bomDescriptionColumn.set_clickable(True)
		self.bomPNColumn.set_clickable(True)
		self.bomQuantityColumn.set_clickable(True)
		
		#self.bomNameColumn.set_sort_indicator(True)
		#self.bomValueColumn.set_sort_indicator(True)
		#self.bomDeviceColumn.set_sort_indicator(True)
		#self.bomPackageColumn.set_sort_indicator(True)
		#self.bomDescriptionColumn.set_sort_indicator(True)
		#self.bomPNColumn.set_sort_indicator(True)
		#self.bomQuantityColumn.set_sort_indicator(True)
		
		self.bomNameColumn.set_attributes(self.bomNameCell, text=0)
		self.bomValueColumn.set_attributes(self.bomValueCell, text=1)
		self.bomDeviceColumn.set_attributes(self.bomDeviceCell, text=2)
		self.bomPackageColumn.set_attributes(self.bomPackageCell, text=3)
		self.bomDescriptionColumn.set_attributes(self.bomDescriptionCell, text=4)
		self.bomPNColumn.set_attributes(self.bomPNCell, text=5)
		self.bomQuantityColumn.set_attributes(self.bomQuantityCell, text=6)
		
		self.bomNameColumn.connect("clicked", self.bomSortCallback)
		self.bomValueColumn.connect("clicked", self.bomSortCallback)
		self.bomDeviceColumn.connect("clicked", self.bomSortCallback)
		self.bomPackageColumn.connect("clicked", self.bomSortCallback)
		self.bomDescriptionColumn.connect("clicked", self.bomSortCallback)
		self.bomPNColumn.connect("clicked", self.bomSortCallback)
		self.bomQuantityColumn.connect("clicked", self.bomSortCallback)
		
		self.bomTreeView.set_reorderable(True)
		self.bomTreeView.set_enable_search(True)
		self.bomTreeView.set_headers_clickable(True)
		self.bomTreeView.set_headers_visible(True)
		
		self.bomTreeView.append_column(self.bomNameColumn)
		self.bomTreeView.append_column(self.bomValueColumn)
		self.bomTreeView.append_column(self.bomDeviceColumn)
		self.bomTreeView.append_column(self.bomPackageColumn)
		self.bomTreeView.append_column(self.bomDescriptionColumn)
		self.bomTreeView.append_column(self.bomPNColumn)
		self.bomTreeView.append_column(self.bomQuantityColumn)
		#self.projectStorePopulate()
		
		self.bomTreeView.connect("cursor-changed", self.bomSelectionCallback)
		self.bomTreeView.set_model(self.bomStore)
		
		self.bomReadInputButton.connect("clicked", self.readInputCallback, "read")
		self.bomReadDBButton.connect("clicked", self.bomReadDBCallback, "read")
		self.bomEditPartButton.connect("clicked", self.bomEditPartCallback, "setPN")
		
		self.bomScrollWin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		
		# TODO: Fiddle with bomTable sizing to make it force the window larger to fit
		
		self.bomGroupName.connect("toggled", self.bomGroupCallback, "name")
		self.bomGroupValue.connect("toggled", self.bomGroupCallback, "value")
		self.bomGroupPN.connect("toggled", self.bomGroupCallback, "product")
		
		self.partInfoVendorLabel1.set_alignment(0.0, 0.5)
		self.partInfoVendorLabel2.set_alignment(0.0, 0.5)
		self.partInfoVendorPNLabel1.set_alignment(0.0, 0.5)
		self.partInfoVendorPNLabel2.set_alignment(0.0, 0.5)
		self.partInfoInventoryLabel1.set_alignment(0.0, 0.5)
		self.partInfoInventoryLabel2.set_alignment(0.0, 0.5)
		self.partInfoManufacturerLabel1.set_alignment(0.0, 0.5)
		self.partInfoManufacturerLabel2.set_alignment(0.0, 0.5)
		self.partInfoManufacturerPNLabel1.set_alignment(0.0, 0.5)
		self.partInfoManufacturerPNLabel2.set_alignment(0.0, 0.5)
		self.partInfoDescriptionLabel1.set_alignment(0.0, 0.5)
		self.partInfoDescriptionLabel2.set_alignment(0.0, 0.5)
		self.partInfoDatasheetLabel1.set_alignment(0.0, 0.5)
		self.partInfoDatasheetLabel2.set_alignment(0.0, 0.5)
		self.partInfoCategoryLabel1.set_alignment(0.0, 0.5)
		self.partInfoCategoryLabel2.set_alignment(0.0, 0.5)
		self.partInfoFamilyLabel1.set_alignment(0.0, 0.5)
		self.partInfoFamilyLabel2.set_alignment(0.0, 0.5)
		self.partInfoSeriesLabel1.set_alignment(0.0, 0.5)
		self.partInfoSeriesLabel2.set_alignment(0.0, 0.5)
		self.partInfoPackageLabel1.set_alignment(0.0, 0.5)
		self.partInfoPackageLabel2.set_alignment(0.0, 0.5)
		
		self.dbScrollWin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		self.dbReadDBButton.connect("clicked", self.dbReadDBCallback, "read")
		
		# -------- PACKING AND ADDING --------
		self.mainBox.pack_start(self.menuBar)
		self.mainBox.pack_start(self.notebook)
		self.window.add(self.mainBox)
		
		# Project selection tab
		self.projectBox.pack_start(self.projectToolbar)
		self.projectToolbar.insert(self.projectNewButton, 0)
		self.projectToolbar.insert(self.projectOpenButton, 1)
		self.projectToolbar.insert(self.projectEditButton, 2)
		self.projectToolbar.insert(self.projectDeleteButton, 3)
		
		self.projectBox.pack_start(self.projectFrame)
		self.projectFrame.add(self.projectScrollWin)
		self.projectScrollWin.add_with_viewport(self.projectTreeView)
		
		self.newProjectNameHBox.pack_start(self.newProjectNameLabel, False, True, 0)
		self.newProjectNameHBox.pack_end(self.newProjectNameEntry, False, True, 0)
		
		self.newProjectDescriptionHBox.pack_start(self.newProjectDescriptionLabel, False, True, 0)
		self.newProjectDescriptionHBox.pack_end(self.newProjectDescriptionEntry, False, True, 0)
		
		#self.newProjectDatabaseFileHBox.pack_start(self.newProjectDatabaseFileLabel, False, True, 0)
		#self.newProjectDatabaseFileHBox.pack_end(self.newProjectDatabaseFileEntry, False, True, 0)
		
		self.newProjectInputFileHBox.pack_start(self.newProjectInputFileLabel, False, True, 0)
		self.newProjectInputFileHBox.pack_start(self.newProjectInputFileEntry, False, True, 0)
		self.newProjectInputFileHBox.pack_end(self.newProjectInputFileButton, False, True, 0)
		
		self.newProjectDialog.vbox.set_spacing(1)
		self.newProjectDialog.vbox.pack_start(self.newProjectNameHBox, True, True, 0)
		self.newProjectDialog.vbox.pack_start(self.newProjectDescriptionHBox, True, True, 0)
		#self.newProjectDialog.vbox.pack_start(self.newProjectDatabaseFileHBox, True, True, 0)
		self.newProjectDialog.vbox.pack_start(self.newProjectInputFileHBox, True, True, 0)
		
		self.newProjectDialog.vbox.show_all()
		
		# BOM tab elements
		
		self.bomTabBox.pack_start(self.bomToolbar)
		self.bomToolbar.insert(self.bomReadInputButton, 0)
		self.bomToolbar.insert(self.bomReadDBButton, 1)
		self.bomToolbar.insert(self.bomEditPartButton, 2)
		
		# TODO : Add toolbar elements
		
		self.bomTabBox.pack_start(self.bomHPane)
		self.bomHPane.pack1(self.bomFrame, True, True)
		self.bomHPane.add2(self.bomVPane)
		self.bomVPane.add1(self.partInfoFrame)
		self.bomVPane.add2(self.pricingFrame)
		
		# BOM Frame elements
		self.bomFrame.add(self.bomScrollBox)
		
		self.bomScrollBox.pack_start(self.bomScrollWin, True, True, 0)
		self.bomScrollWin.add_with_viewport(self.bomTreeView)
		self.bomScrollBox.pack_end(self.bomRadioBox, False, False, 0)

		self.bomRadioBox.pack_start(self.bomRadioLabel)
		self.bomRadioBox.pack_start(self.bomGroupName)
		self.bomRadioBox.pack_start(self.bomGroupValue)
		self.bomRadioBox.pack_start(self.bomGroupPN)
		
		# Part info frame elements
		self.partInfoFrame.add(self.partInfoRowBox)
		self.partInfoRowBox.pack_start(self.partInfoInfoTable, True, True, 5)
		self.partInfoInfoTable.attach(self.partInfoVendorLabel1, 0, 1, 0, 1)
		self.partInfoInfoTable.attach(self.partInfoVendorPNLabel1, 0, 1, 1, 2)
		self.partInfoInfoTable.attach(self.partInfoInventoryLabel1, 0, 1, 2, 3)
		self.partInfoInfoTable.attach(self.partInfoManufacturerLabel1, 0, 1, 3, 4)
		self.partInfoInfoTable.attach(self.partInfoManufacturerPNLabel1, 0, 1, 4, 5)
		self.partInfoInfoTable.attach(self.partInfoDescriptionLabel1, 0, 1, 5, 6)
		self.partInfoInfoTable.attach(self.partInfoDatasheetLabel1, 0, 1, 6, 7)
		self.partInfoInfoTable.attach(self.partInfoCategoryLabel1, 0, 1, 7, 8)
		self.partInfoInfoTable.attach(self.partInfoFamilyLabel1, 0, 1, 8, 9)
		self.partInfoInfoTable.attach(self.partInfoSeriesLabel1, 0, 1, 9, 10)
		self.partInfoInfoTable.attach(self.partInfoPackageLabel1, 0, 1, 10, 11)
		
		self.partInfoInfoTable.attach(self.partInfoVendorLabel2, 1, 2, 0, 1)
		self.partInfoInfoTable.attach(self.partInfoVendorPNLabel2, 1, 2, 1, 2)
		self.partInfoInfoTable.attach(self.partInfoInventoryLabel2, 1, 2, 2, 3)
		self.partInfoInfoTable.attach(self.partInfoManufacturerLabel2, 1, 2, 3, 4)
		self.partInfoInfoTable.attach(self.partInfoManufacturerPNLabel2, 1, 2, 4, 5)
		self.partInfoInfoTable.attach(self.partInfoDescriptionLabel2, 1, 2, 5, 6)
		self.partInfoInfoTable.attach(self.partInfoDatasheetLabel2, 1, 2, 6, 7)
		self.partInfoInfoTable.attach(self.partInfoCategoryLabel2, 1, 2, 7, 8)
		self.partInfoInfoTable.attach(self.partInfoFamilyLabel2, 1, 2, 8, 9)
		self.partInfoInfoTable.attach(self.partInfoSeriesLabel2, 1, 2, 9, 10)
		self.partInfoInfoTable.attach(self.partInfoPackageLabel2, 1, 2, 10, 11)
			
		self.partInfoRowBox.pack_start(self.partInfoPricingTable, True, True, 5)
		self.partInfoRowBox.pack_start(self.partInfoButtonBox)
		
		self.dbBox.pack_start(self.dbToolbar, False)
		self.dbToolbar.insert(self.dbReadDBButton, 0)
		self.dbBox.pack_start(self.dbFrame)
		self.dbFrame.add(self.dbScrollWin)
		self.dbScrollWin.add_with_viewport(self.dbTable)
		self.dbTableHeaders()
		self.dbTable.set_col_spacings(10)
		
		self.dbReadDBCallback(None)
		# Show everything
		self.mainBox.show_all()
		self.window.show()

def main():
	gtk.main()
	
if __name__ == "__main__":
	URBM()
	main()
