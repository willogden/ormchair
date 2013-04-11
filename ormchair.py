'''
Created on 24 Jan 2013

@author: will
'''
import requests
import uuid
import json
import copy

"""
Stores a mapping of document classes against name
"""
type_class_map = {}


"""
Used for schema validation errors
"""
class ValidationError(Exception):
	def __init__(self, message):
		Exception.__init__(self, message)

"""
Used for document conflict errors
"""
class ConflictError(Exception):
	def __init__(self, message):
		Exception.__init__(self, message)


"""
Represents an abstract property of a class
"""
class Property(object):
	
	# Stores the actual value of the property
	def __init__(self,*args,**kwargs):
		
		self._name = None
		self._required = kwargs.pop('required', None)
		self._default = kwargs.pop('default', None)
		
	def __get__(self, instance, owner):
		
		if instance is None:
			return self
		else:
			# Has it been previously set?
			if self._name in instance._property_values:
				return instance._property_values[self._name]
			else:
				return None
	
	def __set__(self, instance, value):
		
		if instance:
			
			if self._validate(value):
				instance._property_values[self._name] = value
	
	
	# Set the name of the property
	def setName(self,name):
		
		self._name = name
	
	# Get the name of the property
	def getName(self):
		
		return self._name
	
	# Get whether this is required
	def getRequired(self):
		
		return self._required
		
	# Override	
	def _validate(self,value):
		
		return True
	
	# Override
	def instanceToDict(self,instance):
		
		return self.__get__(instance, None)
	
	# Override
	def schemaToDict(self):
		
		schema_dict = {}
		
		if self._required:
			schema_dict["required"] = True
		
		return schema_dict
		
	
	# Return the default value
	def getDefaultValue(self):
		
		if hasattr(self,"_default"):
			return self._default
		else:
			return None
		
	
""" 
Metaclass to set the name on the descriptor property objects
"""
class SchemaMetaClass(type):
	
	def __new__(cls, classname, bases, classDict):
		
		# Store a static variable of the property names
		classDict["_properties"] = []
		for base in bases:
			if hasattr(base,"_properties"):
				classDict["_properties"].extend(base._properties)

		# Iterate through the new class' __dict__ and update all recognised property names
		for name, attr in classDict.iteritems():
			
			if isinstance(attr, Property):
				
				# Store the name of the property in the descriptor
				attr.setName(name)
				
				# Append the name of the property to class var
				classDict["_properties"].append(name)
				
		# Create a class
		schema_class =  type.__new__(cls, classname, bases, classDict)
		
		return schema_class

"""
Mapped to a class
"""
class Schema(object):
	
	# Set the name on all the descriptors within this class
	__metaclass__ = SchemaMetaClass
	
	# Is this a root schema or subschema
	_is_root = True
	
	def __init__(self,root_instance=None):
		
		# Store the root instance (if none then assumed is root instance)
		self._root_instance = root_instance if root_instance else self
		
		# Used to store actual values of properties (can't store in descriptor objects as they are static)
		self._property_values = {}

		# Used to store unknown property values e.g. ones that don't match the schema but are passed in
		self._unknown_property_values = []
		
		# Set parent and defaults on properties
		for property_name in self._properties:
			
			# Defaults
			default_value = getattr(self.__class__,property_name).getDefaultValue()
			setattr(self,property_name,default_value)
	
	# Set the values of the schema from a dict	
	def instanceFromDict(self,dict_data,ignore_properties=None):
		
		# If this is a root level schema empty the unknown properties list
		if self.__class__._is_root:
			
			del self.getUnknownPropertyValues()[:]
			
		if isinstance(dict_data,dict):
			
			# Loop known properties
			for property_name in self._properties:
				
				if property_name in dict_data:
					setattr(self,property_name,dict_data[property_name])
				elif getattr(self.__class__,property_name).getRequired():
					raise ValidationError("Property %s is required but not present" % property_name)
			
			# Convert to sets
			data_set = set(dict_data.keys())
			properties_set = set(self._properties)
			
			# Remove keys to ignore (they're probably handled elsewhere by a subclass)
			data_set = data_set - set(ignore_properties) if ignore_properties else data_set
			
			# Get the unknowns
			unknown_properties_set = data_set.difference(properties_set)
			for unknown_property in unknown_properties_set:
				self.getUnknownPropertyValues().append(unknown_property)
			
	
	# Export the schemas values as a basic dict
	def instanceToDict(self):
		
		dict_data = {}
		
		# Loop over properties
		for property_name in self._properties:
			
			dict_data[property_name] = getattr(self.__class__,property_name).instanceToDict(self)
		
		return dict_data
	
	# Returns the root level instance object e.g. for dict and list properties to know their parent
	def getRootInstance(self):
		
		return self._root_instance
	
	def getUnknownPropertyValues(self):
		
		return self._unknown_property_values
	
	# Export the class schema as a dict
	@classmethod
	def schemaToDict(cls):
		
		schema_dict = {
			"type" : "object",
			"properties" : {},		
		}
		
		# If this is a root schema add extras
		if cls._is_root:
			schema_dict["$schema"] = "http://json-schema.org/draft-03/schema#"
			schema_dict["id"] = cls.__name__.lower()
			
		# Loop over properties
		
		links = []
		for property_name in cls._properties:
			
			# Get the property
			cls_property = getattr(cls,property_name)
			
			# Treat linkproperties differently
			if isinstance(cls_property,LinkProperty):
				links.append(cls_property.schemaToDict())
			else:
				schema_dict["properties"][property_name] = cls_property.schemaToDict()
			
		# Only add links if there are any
		if len(links) > 0:
			schema_dict["links"] = links
		
		return schema_dict
	

"""
A string property of a class
"""
class StringProperty(Property):
	
	def __init__(self,*args,**kwargs):
		
		self._minLength = kwargs.pop('minLength', None)
		self._maxLength = kwargs.pop('maxLength', None)
		
		# Not implemented
		self._format = kwargs.pop('format', None)
		self._pattern = kwargs.pop('pattern', None)
		
		super(StringProperty, self).__init__(self,*args,**kwargs)
		
	
	# Override	
	def _validate(self,value):
		
		if value and not isinstance(value, basestring):
			raise ValidationError("Not a string")
		
		# Check minimum length
		if value and self._minLength and len(value) < self._minLength:
			raise ValidationError("String is less than minimum length")
			
		# Check maximum
		if value and self._maxLength and len(value) > self._maxLength:
			raise ValidationError("String is greater than maximum length")
		
		return True
	
	# Override
	def schemaToDict(self):
		
		schema_dict = super(StringProperty,self).schemaToDict()
		
		schema_dict["type"] = "string"

		if self._default:
			schema_dict["default"] = str(self._default)
		
		if self._minLength:
			schema_dict["minLength"] = self._minLength
		
		if self._maxLength:
			schema_dict["maxLength"] = self._maxLength
			
		return schema_dict

"""
A number property of a class
"""
class NumberProperty(Property):
	
	def __init__(self,*args,**kwargs):
		
		self._minimum = kwargs.pop('minimum', None)
		self._maximum = kwargs.pop('maximum', None)
		
		# Not implemented yet
		self.format =kwargs.pop('format', None)
		self.divisibleBy = kwargs.pop('divisibleBy', None)
		
		super(NumberProperty, self).__init__(self,*args,**kwargs)
		
	# Override	
	def _validate(self,value):
		
		# Check type
		if value and not isinstance(value, (int, long, float, complex)):
			raise ValidationError("Not a number")
		
		# Check minimum
		if value and self._minimum and value < self._minimum:
			raise ValidationError("Number is less than minimum")
			
		# Check maximum
		if value and self._maximum and value > self._maximum:
			raise ValidationError("Number is greater than maximum")
			
		return True
	
	# Override
	def schemaToDict(self):
		
		schema_dict = super(NumberProperty,self).schemaToDict()
		
		schema_dict["type"] = "number"
		
		if self._default:
			schema_dict["default"] = self._default
		
		if self._minimum:
			schema_dict["minimum"] = self._minimum
		
		if self._maximum:
			schema_dict["maximum"] = self._maximum
			
		return schema_dict
			

"""
An integer property of a class
"""
class IntegerProperty(NumberProperty):
	
	def __init__(self,*args,**kwargs):
		super(IntegerProperty, self).__init__(self,*args,**kwargs)
	
	# Override	
	def _validate(self,value):
		
		if value and not isinstance(value, int):
			raise ValidationError("Not a number")
		
		return True
	
	# Override
	def schemaToDict(self):
		
		schema_dict = super(IntegerProperty,self).schemaToDict()
		schema_dict["type"] = "integer"
		
		return schema_dict
	

"""
A boolean property of a class
"""
class BooleanProperty(Property):
	
	def __init__(self,*args,**kwargs):
		
		# Not implemented
		self._format = kwargs.pop('format', None)
		
		super(BooleanProperty, self).__init__(self,*args,**kwargs)
		
	
	# Override	
	def _validate(self,value):
		
		if value and not isinstance(value, bool):
			raise ValidationError("Not a boolean")
		
		return True
	
	# Override
	def schemaToDict(self):
		
		schema_dict = {"type":"boolean"}
		
		return schema_dict


"""
Allows for composite properties
"""
class DictProperty(Property):
	
	def __init__(self,*args,**kwargs):
		
		super(DictProperty, self).__init__(self,*args,**kwargs)
		
		# Create a new subclass of Schema
		kwargs["_is_root"] = False
		self._cls = type('SchemaSubClass', (Schema,), kwargs)
		
	def __get__(self, instance, owner):
		
		if instance is None:
			# Return descriptor
			return self
		else:
			self._checkForPropertyValue(instance)

			# Return instance of subclass
			return instance._property_values[self._name]
	

	def __set__(self, instance, value):
		
		self._checkForPropertyValue(instance)
		
		instance._property_values[self._name].instanceFromDict(value)
	
	# Make sure property value has been set	
	def _checkForPropertyValue(self,instance):
		# Check to see if property exists on instance
		if self._name not in instance._property_values:
				
			# Create instance of schema subclass
			instance._property_values[self._name] = self._cls(root_instance=instance.getRootInstance())
	
	def instanceToDict(self,instance):
		
		property_data = {}
		
		# Get the instance of the dict_property subclass
		dict_property_instance = getattr(instance,self._name)
		
		# Loop the properties
		for property_name in dict_property_instance._properties:	
			# Recurse on instanceToDict
			property_data[property_name] = getattr(dict_property_instance.__class__,property_name).instanceToDict(dict_property_instance)
		
		return property_data
	
	def valueFromDict(self,instance,dict_data):
		
		# Loop the properties
		for property_name in instance._properties:	
			
			# Set the instance value
			setattr(instance,property_name,dict_data[property_name])
	
	def schemaToDict(self):
		
		return self._cls.schemaToDict()
	

# Thanks to http://stackoverflow.com/questions/12201811/subclass-python-list-to-validate-new-items
class DictPropertyList(list):
	
	def __init__(self, itr, cls, root_instance): 
		
		self._cls = cls
		self._root_instance = root_instance
		
		# If a list has been passed in then validate
		if itr == None:
			itr = []
		else:
			itr = map(self._validate, itr)
		
		super(DictPropertyList, self).__init__(itr)

	# Unbound method just stored in class for encapsulation
	def wrap(f, takes_list=False, validate_arg_index=0):
		def wrapped_f(self,*args):
			
			# args is tuple which is immutable
			list_args = list(args)
			
			# Do we need to map each item to validate function?
			if takes_list:
				list_args[validate_arg_index] = map(self._validate, args[validate_arg_index])
			else:
				list_args[validate_arg_index] = self._validate(args[validate_arg_index])
			
			return f(self,*list_args)
		return wrapped_f
	
	# Check value is ok
	def _validate(self, value):
		
		# Create a new instance of Schema subclass
		list_instance = self._cls(root_instance=self._root_instance)
		
		# Wrap the value into a dict
		instance_dict = {"_property": value}
		
		# Populate from dict (and thus validate)
		list_instance.instanceFromDict(instance_dict)
		
		return list_instance
	
	# Need to override as we only want the value of the _property property
	def __getitem__(self,index):
		
		list_instance = super(DictPropertyList, self).__getitem__(index)
		
		return list_instance._property
	
	# Override all methods that add an item to the list
	append = wrap(list.append)
	extend = wrap(list.extend,takes_list=True)
	insert = wrap(list.insert,validate_arg_index=1)
	__add__ = wrap(list.__add__,takes_list=True)
	__iadd__ = wrap(list.__iadd__,takes_list=True)
	__setitem__ = wrap(list.__setitem__)
	__setslice__ = wrap(list.__setslice__,takes_list=True)		

""" 
Special property that represents an list property
"""
class ListProperty(Property):
	
	def __init__(self,property_instance,*args,**kwargs):
		
		super(ListProperty, self).__init__(self,*args,**kwargs)
		
		# Create a new subclass of Schema based on passed in property instance
		kwargs = {"_is_root" : False, "_property" : property_instance}
		self._cls = type('SchemaSubClass', (Schema,), kwargs)
		
	# Get
	def __get__(self, instance, owner):
		
		if instance is None:
			# Return descriptor
			return self
		else:
			
			# If first time accessed set default
			if self._name not in instance._property_values:
				
				# Create instance of schema subclass
				self.__set__(instance,[])
				
			# Return instance of subclass
			return instance._property_values[self._name]
	
	# Set
	def __set__(self, instance, value):
		
		if value == None:
			value = []
		
		# Store a dictpropertylist on the instance
		instance._property_values[self._name] = DictPropertyList(value,self._cls,instance.getRootInstance())
		

	# Get the object as JSON
	def instanceToDict(self,instance):
		
		# Empty array
		list_data = []
		
		# Loop over dictpropertlist
		for item in self.__get__(instance,None):
			
			# Only interested in the value of the _property property
			list_data.append(item.instanceToDict()["_property"])
				
		return list_data
	
	def schemaToDict(self):
		
		return {
			"items" : self._cls._property.schemaToDict()
		}


"""
Property to link to other schemas
"""
class LinkProperty(Property):
	
	def __init__(self,linked_class,*args,**kwargs):
		
		self._linked_class = linked_class
		self._reverse = kwargs.pop('reverse', None)
		
		super(LinkProperty,self).__init__(*args,**kwargs)
		
		# Add a reverse relation
		if self._reverse and not hasattr(self._linked_class,self._reverse):
			
			setattr(self._linked_class,self._reverse,LinkProperty(self.__class__,reverse=self._name))
		
	def __get__(self, instance, owner):
		
		if instance:
			return (instance,self)
		else:
			return self
			
	def __set__(self, instance, value):
		pass
	
	def instanceToDict(self,instance):
		
		return None
	
	def getLinkedClass(self):
		
		return self._linked_class
	
	def getReverse(self):
		
		return self._reverse
	
	# Override
	def schemaToDict(self):
		
		return {
			"href" : ("/%s") % (self.getName()),
			"rel" : self.getName(),
			"$targetSchema" : ("%s#") % self._linked_class.__name__.lower()
		}

"""
Embedded link helper class
"""
class EmbeddedLink():
	
	_id = StringProperty()
	
	def __init__(self):
		
		self._id = None
		self._document = None
		self._inflated = False

"""
Allows for composite properties
"""
class EmbeddedLinkProperty(Property):
	
	def __init__(self,linked_class,**kwargs):
		
		self._linked_class = linked_class
		
		super(EmbeddedLinkProperty, self).__init__(self,**kwargs)
	
	def __get__(self, instance, owner):
		
		if instance is None:
			# Return descriptor
			return self
		else:
			self._checkForPropertyValue(instance)

			# If _inflated is True return the doc
			if instance._property_values[self._name]._inflated:
				return instance._property_values[self._name]._document
			else:
				# Return id
				return instance._property_values[self._name]._id
	

	def __set__(self, instance, value):
		
		self._checkForPropertyValue(instance)
		
		# If value is a an instance of linked class then this is the data to inflate this property else it's just an id
		if isinstance(value,self._linked_class):
			instance._property_values[self._name]._inflated = True
			instance._property_values[self._name]._document = value
			instance._property_values[self._name]._id = value._id
		else:
			instance._property_values[self._name]._id = value
	
	# Make sure property value has been set	
	def _checkForPropertyValue(self,instance):
		# Check to see if property exists on instance
		if self._name not in instance._property_values:
				
			instance._property_values[self._name] = EmbeddedLink()
			
	def instanceToDict(self,instance):
		
		if instance:
			return instance._property_values[self._name]._id
		else:
			return None
	
	# Override
	def schemaToDict(self):
		
		schema_dict = super(EmbeddedLinkProperty,self).schemaToDict()
		
		schema_dict["type"] = [
			{"$ref": ("%s#") % self._linked_class.__name__.lower()},
			"string"
		]
		
		return schema_dict
		


	
"""
A couchdb server
"""
class Server(object):
	
	def __init__(self,url):
		self._url = url
		
	def createDatabase(self,database_name):
		
		# TODO check the database name is valid
		database_url = "%s/%s/" % (self._url, database_name)
		r = requests.put(database_url)
		
		if r.status_code == 201:
			return Database(database_url)
		else:
			raise Exception(r.json())
		
	def getDatabase(self,database_name):
		
		database_url = "%s/%s/" % (self._url, database_name)
		r = requests.get(database_url)
		
		if r.status_code == 200:
			return Database(database_url, info=r.json())
		else:
			raise Exception(r.json())
	
	def databaseExists(self,database_name):
		
		database_url = "%s/_all_dbs" % (self._url)
		r = requests.get(database_url)
		
		if r.status_code == 200:
			return True if database_name in r.json() else False
		else:
			raise Exception(r.json())
		

"""
Represents a couchdb database
"""
class Database(object):
	
	def __init__(self,database_url,info = None):
		self._database_url = database_url
		self._info = info
	
	def getUrl(self):
		return self._database_url
	
	def delete(self):
		r = requests.delete(self._database_url)
		
		if r.status_code == 404:
			raise Exception(r.json())
	
	# Add single document
	def add(self,document):
		
		data = json.dumps(document.instanceToDict())
		
		r = requests.put("%s/%s" % (self._database_url,document._id),data=data)
		
		if r.status_code == 201:
			document._rev = r.json()["rev"]		
		else:
			raise Exception(r.json())
		
		return document
	
	# Updates a document
	def update(self,document):
		
		data = json.dumps(document.instanceToDict())
		
		r = requests.put("%s/%s" % (self._database_url,document._id),data=data)
		if r.status_code == 201:
			document._rev = r.json()["rev"]
		else:
			raise Exception(r.json())
		
		return document
	
	# Get single document
	def get(self,_id,rev=None,as_json=False):
		
		params = {}
		if rev:
			params = {"rev" : rev}
		
		r = requests.get("%s/%s" % (self._database_url,_id), params = params)
		
		if r.status_code == 200:
			document_data = r.json()
			
			# See if just need to return json
			if as_json:
				return document_data
			
			# Get the correct class (if not fall back to document) 
			if document_data["type_"] in BaseDocument.type_class_map:
				
				#document_class = type_class_map[document_data["type_"]]["class"]
				document_class = BaseDocument.type_class_map[document_data["type_"]]
			else:
				document_class = Document
			
			return document_class(document_data=document_data)
			
		else:
			raise Exception(r.json())
	
	
	# Bulk doc API used for add/update/delete multiple	
	def _bulkDocs(self,documents):
		
		docs_dict = {"docs": [document.instanceToDict() for document in documents]}
		
		headers = {"content-type": "application/json"}	
		data = json.dumps(docs_dict)
		
		r = requests.post("%s/_bulk_docs" % (self._database_url),headers=headers,data=data)
		
		if r.status_code == 201:
			documents_data = r.json()
			
			# Return saved and failed documents
			ok_documents = []
			failed_documents = []
			
			# Create a hash map of id vs new rev (only succeeded updates/inserts will have a rev)
			id_rev_map = dict([(document_data["id"],document_data["rev"]) for document_data in documents_data if "rev" in document_data])
			
			# Update existing objects
			for document in documents:
				
				# See if succeeded
				if document._id in id_rev_map:
					
					document._rev = id_rev_map[document._id]
					ok_documents.append(document)
				
				# Failed due to conflict
				else:
					failed_documents.append(document)
					
			return (ok_documents,failed_documents)
			
		else:
			raise Exception(r.json())
	
	# Add multiple documents
	def addMultiple(self,documents):
		return self._bulkDocs(documents)
	
	# Update multiple documents
	def updateMultiple(self,documents):
		return self._bulkDocs(documents)
	
	# Delete multiple documents
	def deleteMultiple(self,documents):
		
		# Mark all docs for delete
		for document in documents:
			document.setMarkedForDelete(True)
			
		return self._bulkDocs(documents)
	
	
	# Pass a json response from a view query and inflates documents
	def _processViewResponse(self,documents_data,as_json=False):
		
		documents = []
			
		for row in documents_data["rows"]:
			
			if as_json:
				
				documents.append(row["doc"])
				
			else:
				
				# Get the correct class (if not fall back to document) 
				if row["doc"]["type_"] in BaseDocument.type_class_map:
					document_class = BaseDocument.type_class_map[row["doc"]["type_"]]
				else:
					document_class = Document
			
				documents.append(document_class(document_data=row["doc"]))
		
		return documents
	
	# Get multiple documents
	def getMultiple(self,_ids):
		
		headers = {"content-type": "application/json"}	
		data = json.dumps({"keys":_ids})
		
		r = requests.post("%s/_all_docs?include_docs=true" % (self._database_url), headers=headers,data=data)
		
		if r.status_code == 200:
			
			return self._processViewResponse(r.json())
		
		else:
			raise Exception(r.json())
	
	
	# Add links to documents
	def addLinks(self,link_property,to_documents):
		
		# Get the from doc and property itself
		(from_document,link_property) = link_property
		
		# Check to make sure documents have been added to the db
		documents_to_add = []
		if not from_document.hasBeenAdded():
			documents_to_add.append(from_document)
			
		# Create new link document per to document
		for to_document in to_documents:
			if not to_document.hasBeenAdded():
				documents_to_add.append(to_document)
		
			# Now create link documents
			to_link_document = _LinkDocument()
			to_link_document.name = link_property.getName()
			to_link_document.from_id = from_document._id
			to_link_document.from_type = from_document.type_
			to_link_document.to_id = to_document._id
			to_link_document.to_type = to_document.type_
			
			from_link_document = _LinkDocument()
			from_link_document.name = link_property.getReverse()
			from_link_document.from_id = to_document._id
			from_link_document.from_type = to_document.type_
			from_link_document.to_id = from_document._id
			from_link_document.to_type = from_document.type_
			
			# Add documents to database
			documents_to_add.extend([to_link_document,from_link_document])
		
		return self.addMultiple(documents_to_add)
	
	# Add link to document
	def addLink(self,link_property,to_document):
		
		return self.addLinks(link_property, [to_document])
	
	def getLinks(self,link_property,start_key=None,limit=None,as_json=False):
		
		# Get the from doc and property itself
		(from_document,link_property) = link_property
		
		start_key = [link_property.getName(),from_document._id,start_key] if start_key else [link_property.getName()]
		end_key = [link_property.getName(),from_document._id,{}]
		
		params = {
			"include_docs" : not as_json,
			"startkey" : json.dumps(start_key),
			"endkey" : json.dumps(end_key)
		}
		
		if limit:
			params["limit"] = limit
			
		r = requests.get("%s%s/_view/links_" % (self._database_url,from_document.getSchemaDesignDocumentId()), params = params)
		
		if r.status_code == 200:
			
			return self._processViewResponse(r.json(),as_json)
		
		else:
		
			raise Exception(r.json())
	
	def deleteLink(self,link_property,to_document):
		
		self.deleteLinks(link_property,[to_document])
	
	def deleteLinks(self,link_property,to_documents):
		
		# Get the from doc and property itself
		(from_document,link_property) = link_property
		
		_ids = []
		
		headers = {"content-type": "application/json"}	
		data = json.dumps({"keys":_ids})
		
		r = requests.post("%s/_design/_linkdocument/_view/get_by_name" % (self._database_url,from_document.getSchemaDesignDocumentId()), headers=headers,data=data)
		
		
		# Now get reverse documents
		if link_property.getReverse():
			linked_class = link_property.getLinkedClass()
			
		
	# Loops over document classes and creates their schema's and if changed updates schema version and design docs for indexes
	def sync(self):
		
		# Loop each document class
		for document_class_name in BaseDocument.type_class_map:
			
			document_class = BaseDocument.type_class_map[document_class_name]
			
			# Don't sync design documents and system documents (seperate process for them)
			if not issubclass(document_class, DesignDocument) and document_class not in [BaseDocument,Document,_LinkDocument]:
				
				saved_schema_design_document = None
				
				try:
					
					# Try and get
					saved_schema_design_document = self.get(document_class.getSchemaDesignDocumentId())
					
					# Got this far so must compare to see if it needs updating
					current_schema_design_document = document_class.getSchemaDesignDocument()
					
					# Set the _rev properties so like for like comparison
					current_schema_design_document._rev = saved_schema_design_document._rev

					if json.dumps(current_schema_design_document.instanceToDict()) != json.dumps(saved_schema_design_document.instanceToDict()):
						
						saved_schema_design_document = self.update(current_schema_design_document)
	
				# Add
				except Exception:
					
					saved_schema_design_document = self.add(document_class.getSchemaDesignDocument())
						
				# Set the schema rev for document class
				document_class.setCurrentSchemaRev(saved_schema_design_document._rev)
				
			# Check design documents and see if they have fixed id's...if so check for changes and sync if needed
			elif issubclass(document_class, DesignDocument) and document_class.hasFixedId():
				
				current_design_document = document_class()
				
				try:
					
					saved_design_document = self.get(current_design_document._id)
					current_design_document._rev = saved_design_document._rev
	
					# Compare with saved (also check for unknown properties e.g. things in the doc that aren't in the schema)
					if json.dumps(current_design_document.instanceToDict()) != json.dumps(saved_design_document.instanceToDict()) or len(saved_design_document.getUnknownPropertyValues()) > 0:
						
						saved_design_document = self.update(current_design_document)
				
				except ValidationError:
					
					# Ok doc exists but couldn't create class so just grab document (TODO this is inefficient but only happens when syncing meh)
					saved_design_document_json = self.get(current_design_document._id,as_json=True)
					current_design_document._rev = saved_design_document_json["_rev"]
					saved_design_document = self.update(current_design_document)
					
				except Exception:
					
					# Doc doesn't exist so first sync so just add
					saved_design_document = self.add(current_design_document)
				
	
	# Gets the documents by index
	def getByIndex(self,index_property,key,start_key=None,limit=None):
		
		# Get the parent document class from the property
		document_class = index_property.getParent()
		
		# Append the name of the property to the key
		key.insert(0,index_property.getName())
		
		headers = {"content-type": "application/json"}	
		data = json.dumps({"keys":[key]})
		r = requests.post("%s/%s/_view/indexes_" % (self._database_url, document_class.getSchemaDesignDocumentId()), headers=headers,data=data)
		
		if r.status_code == 200:
			documents = []
			documents_data = r.json()
			
			for row in documents_data["rows"]:
				
				# Get the correct class (if not fall back to document) 
				if row["value"]["type_"] in BaseDocument.type_class_map:
					document_class = BaseDocument.type_class_map[row["value"]["type_"]]
				else:
					document_class = Document
			
				documents.append(document_class(document_data=row["value"]))
			
			return documents
		
		else:
			print r.url
			raise Exception(r.json())
		
"""
Used to create a view that allows documents to queried using a map function
"""
class Index(object):
	
	# args is a list of paths e.g. "address.address_1","name"
	def __init__(self,*args):
		self._property_paths = tuple(["doc." + property_path for property_path in args])

	def setName(self,name):
		self._name = name
	
	def getName(self):
		return self._name
	
	def setParent(self,parent):
		self._parent = parent
	
	def getParent(self):
		return self._parent
	
	def getJSEmitStatement(self):
		
		emit_keys = (self._name,) + self._property_paths
		mask_string = "'%s'" + (",%s" * len(self._property_paths))
		emit_string = "emit([" + mask_string + "],doc);"
		
		return emit_string % emit_keys




"""
Wrapper to set fixed id for a document class e.g. singleton documents
"""
def _id(id):
	def decorator(document_class):
		document_class._fixed_id = id
		return document_class
	return decorator

""" 
Metaclass for basedocument
"""
class BaseDocumentMetaClass(SchemaMetaClass):
	
	def __new__(cls, classname, bases, classDict):

		# Create the new document class
		base_document_class = SchemaMetaClass.__new__(cls, classname, bases, classDict)
		
		# Store in map (this is actually a static)
		base_document_class.type_class_map[classname.lower()] = base_document_class
		
		return base_document_class


"""
The base document class
"""
class BaseDocument(Schema):
	
	__metaclass__ = BaseDocumentMetaClass
	
	# Static to store a mapping between type and class
	type_class_map = {}
	
	# The properties
	_id = StringProperty(required=True)
	_rev = StringProperty(required=True)
	type_ = StringProperty(required=True)
	
	def __init__(self,_id=None,document_data=None):
		
		super(BaseDocument,self).__init__()
		
		# See if data passed in
		if document_data == None:
			
			# Set id if not passed in
			self._id = _id if _id else uuid.uuid1().hex
			
			# Set the classname as the type if not got a default set
			self.type_ = self.type_ if self.type_ else self.__class__.__name__.lower()
			
		else:
			self.instanceFromDict(document_data)
			
		# Store special flag for deletion
		self._marked_for_delete = False
	
	# Get the document as dict
	def instanceToDict(self):
		
		# Empty dict
		document_data = {}
		
		# See if marked for delete
		if self._marked_for_delete:
			document_data["_deleted"] = True
		
		# Loop over properties
		for property_name in self._properties:
			if not (property_name == "_rev" and self._rev == None):
				
				document_data[property_name] = getattr(self.__class__,property_name).instanceToDict(self)		
		
		return document_data
	
	# Has the document been added to the database yet?
	def hasBeenAdded(self):
		
		return not (self._rev == None)
	
	# Mark this document for delete
	def setMarkedForDelete(self,marked_for_delete=True):
		
		self._marked_for_delete = marked_for_delete

""" 
Metaclass for document
"""
class DocumentMetaClass(BaseDocumentMetaClass):
	
	def __new__(cls, classname, bases, classDict):

		# Create the new document class
		document_class = BaseDocumentMetaClass.__new__(cls, classname, bases, classDict)
		
		# Extend statics
		_indexes = []
		for base in bases:
			if hasattr(base,"_indexes"):
				_indexes.extend(base._indexes)
		
		# Iterate through the new class' __dict__ and update all recognised index names
		for name, attr in classDict.iteritems():
			
			if isinstance(attr, Index):
				
				# Store the name of the index in the descriptor
				attr.setName(name)
				
				# Store the parent class in the property
				attr.setParent(document_class)
				
				# Append the name of the index to class var
				_indexes.append(name)
		
		# Set class property
		document_class._indexes = _indexes

		return document_class


"""
The main class to extend. Represents a couchdb schema bound document
"""
class Document(BaseDocument):
	
	__metaclass__ = DocumentMetaClass
	
	# Static map to store the current rev
	_current_schema_rev = {}
	
	# Used to keep track of which schema version created this
	schema_rev_ = StringProperty(required=True)
	
	def __init__(self,_id=None,document_data=None):
		
		super(Document,self).__init__(_id=_id,document_data=document_data)
		
		# See if data passed in
		if document_data == None:
		
			# Store the rev of the current schema that has been used to create this document
			self.schema_rev_ = self.getCurrentSchemaRev()
			
	# Get the current rev for this class
	@classmethod
	def getCurrentSchemaRev(cls):	
		
		if cls.__name__.lower() in Document._current_schema_rev:
			return Document._current_schema_rev[cls.__name__.lower()]
		else:
			return None
	
	# Set the current rev for this class
	@classmethod
	def setCurrentSchemaRev(cls,schema_rev):	
		
		Document._current_schema_rev[cls.__name__.lower()] = schema_rev
	
	# Get the document id
	@classmethod
	def getSchemaDesignDocumentId(cls):
		
		return "_design/_schema_%s" % (cls.__name__.lower())
	
	# Schema design doc contains index and link views
	@classmethod
	def getSchemaDesignDocument(cls):
		
		# Create an instance of the schema document
		schema_design_document = _SchemaDesignDocument(_id=cls.getSchemaDesignDocumentId())

		# Set the schema
		schema_design_document.schema_ = json.dumps(cls.schemaToDict())
		
		# Set the views
		
		# First the indexes
		if len(cls._indexes):
			
			function_string = "function(doc){"
			function_string += "if(doc.type_=='%s'){" % (cls.__name__.lower())
			
			for index_name in cls._indexes:
				index = getattr(cls,index_name)
				function_string += index.getJSEmitStatement()
			function_string += "}}"
			
			
			schema_design_document.indexes_["map"] = function_string
		
		# Now the links
		emit_strings = []
		for property_name in cls._properties:
			
			# Get the property
			cls_property = getattr(cls,property_name)
			
			# Is this a link property
			if isinstance(cls_property,LinkProperty):
				
				emit_string = "emit(['%s',doc.from_id,doc.to_id],{'_id': doc.to_id});" % (cls_property.getName())
				emit_strings.append(emit_string)
		
		if len(emit_strings) > 0:
			function_string = "function(doc){"
			function_string += "if(doc.type_=='_linkdocument' && doc.from_type == '%s'){" % (cls.__name__.lower())
			for emit_string in emit_strings:
				function_string += emit_string
			function_string += "}}"
			
			schema_design_document.links_["map"] = function_string
		
		return schema_design_document
			
			
"""
Represents a view
"""
class View(object):
	
	# Stores the actual value of the property
	def __init__(self,default_value=None):
		
		self._name = None
		self._default_value = default_value if default_value else {"map" : {}}
			
	def __get__(self, instance, owner):
		
		if instance is None:
			return self
		else:
			self._checkForViewValue(instance)
			
			return instance._view_values[self._name]
			
	def __set__(self, instance, value):
		
		if instance:
			if self._validate(value):
				
				self._checkForViewValue(instance)
				
				instance._view_values[self._name] = value
	
	# Make sure property value has been set	
	def _checkForViewValue(self,instance):
		
		# Check to see if view exists on instance
		if self._name not in instance._view_values:
			
			# If not set default (must deepcopy as object...took a day to find this!)
			instance._view_values[self._name] = copy.deepcopy(self._default_value)

	# Set the name of the property
	def setName(self,name):
		
		self._name = name
	
	# Get the name of the property
	def getName(self):
		
		return self._name
	
	# Set the parent class
	def setParent(self,parent):
		self._parent = parent
	
	# Get the parent class
	def getParent(self):
		return self._parent
	
	# Get the default map reduce dict
	def getDefaultValue(self):
		
		return self._default_value

	# Validate	
	def _validate(self,value):
		
		# Must contain a map function at minimum
		if value and ("map" not in value):
			raise ValidationError("Map function missing")
		
		return True

""" 
Metaclass to for design documents
"""
class DesignDocumentMetaClass(BaseDocumentMetaClass):
	
	def __new__(cls, classname, bases, classDict):
		
		# Create the new document class
		design_document_class = DocumentMetaClass.__new__(cls, classname, bases, classDict)
		
		# Extend statics
		_views = []
		for base in bases:
			if hasattr(base,"_views"):
				_views.extend(base._views)
		
		# Iterate through the new class' __dict__ and update all recognised index names
		for name, attr in classDict.iteritems():
			
			if isinstance(attr, View):
				
				# Store the name of the index in the descriptor
				attr.setName(name)
				
				# Store the parent class in the property
				attr.setParent(design_document_class)
				
				# Append the name of the index to class var
				_views.append(name)
		
		# Set class property
		design_document_class._views = _views

		return design_document_class


"""
A design document
"""
class DesignDocument(BaseDocument):

	__metaclass__ = DesignDocumentMetaClass
	
	def __init__(self,_id=None,document_data=None):
		
		# Used to store actual values of views (can't store in descriptor objects as they are static)
		self._view_values = {}
		
		# Use fixed id if set
		_id = self._fixed_id if hasattr(self,"_fixed_id") else _id

		super(DesignDocument,self).__init__(_id=_id,document_data=document_data)
		
	# Overridden to deal with views
	def instanceToDict(self):
		
		document_data = super(DesignDocument,self).instanceToDict()
		
		document_data["views"] = {}
		
		# Now add in view data
		for view_name in self._views:
			
			document_data["views"][view_name] = getattr(self,view_name)
		
		return document_data
	
	# Set the values of the schema from a dict	
	def instanceFromDict(self,dict_data):
		
		super(DesignDocument,self).instanceFromDict(dict_data,ignore_properties=["views"])
		
		if isinstance(dict_data,dict):
			
			# Loop known views
			for view_name in self.__class__._views:
				
				if "views" in dict_data and view_name in dict_data["views"]:
					
					setattr(self,view_name,dict_data["views"][view_name])
				
				elif "views" in dict_data and view_name not in dict_data["views"]: 
					
					raise ValidationError("View %s is required but not present" % view_name)
						
			# Convert to sets
			data_set = set(dict_data["views"].keys()) if "views" in dict_data else set()
			views_set = set(self.__class__._views)
			
			# Get the unknowns
			unknown_views_set = data_set.difference(views_set)
			
			unknown_views = []
			for unknown_view in unknown_views_set:
				unknown_views.append(unknown_view)
			
			# Store under the single views property
			if len(unknown_views) > 0:	
				self.getUnknownPropertyValues().append({"views": unknown_views})				
	
	# Has the design doc been set an id as part of the class definition (most will have)
	@classmethod
	def hasFixedId(cls):
		
		return hasattr(cls,"_fixed_id") and cls._fixed_id != None
					
	
	
"""
Design document containing schema and indexes view
"""
class _SchemaDesignDocument(DesignDocument):

	# The current schema of the document
	schema_ = StringProperty()
	
	# The indexes view
	indexes_ = View()
	
	# The links view
	links_ = View()


"""
Used to store relationship between documents
"""
class _LinkDocument(Document):
	
	name = StringProperty()
	from_type = StringProperty()
	to_type = StringProperty()
	from_id = StringProperty()
	to_id = StringProperty()
	
	
"""
Design document dealing with links
"""
@_id("_design/_linkdocument")
class _LinkDesignDocument(DesignDocument):

	# Returns the actual link documents (used mostly in delete)
	get_by_name = View({
		"map" :(
			"function(doc) {"
				"if(doc.type_=='_linkdocument') {"
					"emit([doc.from_id,doc.name,doc.to_id],{'_id': doc._id});"
				"}"
			"}"
		)
	})

	
	