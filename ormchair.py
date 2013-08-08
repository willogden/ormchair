'''
ormchair - a Python ORM for CouchDB

Created on 24 Jan 2013

@author: Will Ogden
'''
import requests
from requests.auth import HTTPBasicAuth
import uuid
import json
import copy
import threading
import weakref

class ValidationError(Exception):
	"""
	Used for schema validation errors
	"""
	def __init__(self, message):
		Exception.__init__(self, message)


class ConflictError(Exception):
	"""
	Used for document conflict errors
	"""
	def __init__(self, message):
		Exception.__init__(self, message)

class PropertyPathNotFoundError(Exception):
	"""
	Used for property paths not found errors
	"""
	def __init__(self, message):
		Exception.__init__(self, message)

class Property(object):
	"""
	Represents an abstract property of a class
	"""
	# Stores the actual value of the property
	def __init__(self,**kwargs):
		
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
		
	

class SchemaMetaClass(type):
	""" 
	Metaclass to set the name on the descriptor property objects
	"""
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


class Schema(object):
	"""
	Mapped to a class
	"""
	# Set the name on all the descriptors within this class
	__metaclass__ = SchemaMetaClass
	
	# Is this a root schema or subschema
	_is_root = True
	
	def __init__(self,root_instance=None):
		
		# Store the root instance (if none then assumed is root instance)
		self._root_instance = root_instance if root_instance else self
		
		# Used to store actual values of properties (can't store in descriptor objects as they are static)
		self._property_values = {}

		# Set parent and defaults on properties
		for property_name in self._properties:
			
			# Defaults
			default_value = getattr(self.__class__,property_name).getDefaultValue()
			setattr(self,property_name,default_value)
	
	# Set the values of the schema from a dict	
	def instanceFromDict(self,dict_data,ignore_properties=None):
	
		if isinstance(dict_data,dict):
			
			# Loop known properties
			for property_name in self._properties:
				
				if property_name in dict_data:
					setattr(self,property_name,dict_data[property_name])
					# Remove the item from the dict
					del dict_data[property_name]
				elif getattr(self.__class__,property_name).getRequired():
					raise ValidationError("Property %s is required but not present" % property_name)
			
			if len(dict_data.keys()) > 0:
	
				raise ValidationError("Unknown properties found")

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
	
	@classmethod
	def schemaToDict(cls):
		""" Export the class schema as a JSON-Schema compatible dict """
		
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
	
	def getPropertyValueByPath(self,property_path):
		""" Returns the value of schema property by string path e.g. dict_prop1.dict_prop2.etc """
		
		property_path_list = property_path.split(".")
		property_name = property_path_list.pop(0)

		schema_property = getattr(self,property_name,None)
		
		if schema_property != None and not issubclass(schema_property.__class__,Schema):
			return (True,schema_property)
		elif len(property_path_list) > 0:
			return schema_property.getPropertyValueByPath(".".join(property_path_list))
		else:
			return (False,None)
			#raise PropertyPathNotFoundError("Property path " + property_path + " not found")


class StringProperty(Property):
	"""
	A string property of a class
	"""
	def __init__(self,**kwargs):
		"""
        Kwargs:
        	default (str): Default value
        	required (bool): Is this a required (compulsory) property
           	min_length (int): The minimum value length
           	max_length (int): The maximum value length

        """
		self._min_length = kwargs.pop('min_length', None)
		self._max_length = kwargs.pop('max_length', None)
		
		# Not implemented
		self._format = kwargs.pop('format', None)
		self._pattern = kwargs.pop('pattern', None)
		
		super(StringProperty, self).__init__(**kwargs)
		
	
	# Override	
	def _validate(self,value):
		
		if value and not isinstance(value, basestring):
			raise ValidationError("Not a string")
		
		# Check minimum length
		if value and self._min_length and len(value) < self._min_length:
			raise ValidationError("String is less than minimum length")
			
		# Check maximum
		if value and self._max_length and len(value) > self._max_length:
			raise ValidationError("String is greater than maximum length")
		
		return True
	
	# Override
	def schemaToDict(self):
		
		schema_dict = super(StringProperty,self).schemaToDict()
		
		schema_dict["type"] = "string"

		if self._min_length:
			schema_dict["minLength"] = self._min_length
		
		if self._max_length:
			schema_dict["maxLength"] = self._max_length
			
		return schema_dict


class NumberProperty(Property):
	"""
	A number property of a class
	"""
	def __init__(self,**kwargs):
		"""
		Kwargs:
        	
		"""
		
		self._minimum = kwargs.pop('minimum', None)
		self._maximum = kwargs.pop('maximum', None)
		
		# Not implemented yet
		self.format =kwargs.pop('format', None)
		self.divisible_by = kwargs.pop('divisible_by', None)
		
		super(NumberProperty, self).__init__(**kwargs)
		
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
		
		if self._minimum:
			schema_dict["minimum"] = self._minimum
		
		if self._maximum:
			schema_dict["maximum"] = self._maximum
			
		return schema_dict
			


class IntegerProperty(NumberProperty):
	"""
	An integer property of a class
	"""
	def __init__(self,**kwargs):
		"""
		Kwargs:
        	default (int): Default value
        	required (bool): Is this a required (compulsory) property
			minimum (int): The minimum value
			maximum (int): The maximum value
		"""
		super(IntegerProperty, self).__init__(**kwargs)
	
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
	


class BooleanProperty(Property):
	"""
	A boolean property of a class
	"""
	def __init__(self,**kwargs):
		"""
        Kwargs:
        	default (bool): Default value
        	required (bool): Is this a required (compulsory) property
        """
		# Not implemented
		self._format = kwargs.pop('format', None)
		
		super(BooleanProperty, self).__init__(**kwargs)
		
	
	# Override	
	def _validate(self,value):
		
		if value and not isinstance(value, bool):
			raise ValidationError("Not a boolean")
		
		return True
	
	# Override
	def schemaToDict(self):
		
		schema_dict = {"type":"boolean"}
		
		return schema_dict



class DictProperty(Property):
	"""
	Allows for composite properties
	"""
	def __init__(self,**kwargs):
		"""
        Kwargs:
        	default (dict): Default value
        	required (bool): Is this a required (compulsory) property
        """
		super(DictProperty, self).__init__(**kwargs)
		
		# Create a new subclass of Schema
		kwargs["_is_root"] = False
		self._cls = type('DictPropertySchema', (Schema,), kwargs)
		
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
	
	# Need to override as only need _property value
	def __contains__(self, item):
		
		property_list = map(lambda list_instance: list_instance._property, super(DictPropertyList, self).__iter__())
		return property_list.__contains__(item)
	
	# Need to override as only need _property value
	def __iter__(self):
	
		return map(lambda list_instance: list_instance._property, super(DictPropertyList, self).__iter__()).__iter__()
	
	# Need to override as only need _property value
	def __getslice__(self,i,j):

		return map(lambda list_instance: list_instance._property,  super(DictPropertyList, self).__getslice__(i,j))
	
	# Need to override as only need _property value
	def __eq__(self, other):
		
		return self[:].__eq__(other)
		
	# Override all methods that add an item to the list
	append = wrap(list.append)
	extend = wrap(list.extend,takes_list=True)
	insert = wrap(list.insert,validate_arg_index=1)
	__add__ = wrap(list.__add__,takes_list=True)
	__iadd__ = wrap(list.__iadd__,takes_list=True)
	__setitem__ = wrap(list.__setitem__)
	__setslice__ = wrap(list.__setslice__,takes_list=True)		


class ListProperty(Property):
	""" 
	Represents a list property
	"""
	def __init__(self,property_instance,**kwargs):
		"""
        Args:
        	property_instance (Property): The list item property e.g. each item in the list is an instance of this
        
        Kwargs:
        	default (list): Default value
        	required (bool): Is this a required (compulsory) property
        """
		super(ListProperty, self).__init__(**kwargs)
		
		# Create a new subclass of Schema based on passed in property instance
		kwargs = {"_is_root" : False, "_property" : property_instance}
		self._cls = type('ListPropertySchema', (Schema,), kwargs)
		
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
			
			if issubclass(item.__class__,Schema):
				list_data.append(item.instanceToDict())
			else:
				list_data.append(item)
				
		return list_data
	
	def schemaToDict(self):
		
		return {
			"items" : self._cls._property.schemaToDict()
		}



class LinkProperty(Property):
	"""
	Property to link to other schemas
	"""
	def __init__(self,linked_class,reverse=None,index_property_paths=None,reverse_index_property_paths=None):
		"""
        Args:
			linked_class (Document class): The Document class to create a link to
			reverse (str): The name of the reverse property that will be created on the linked class e.g. the side of the relationship
        	index_property_paths (list): A list of index property paths of the linked class e.g. ["property_1","property_2"]
        	reverse_index_property_paths (list): A list of reverse index property paths of the linked class e.g. ["property_1","property_2"]
        	
        """
		self._linked_class = linked_class
		self._reverse = reverse
		self._index_property_paths = index_property_paths if index_property_paths else []
		self._reverse_index_property_paths = reverse_index_property_paths if reverse_index_property_paths else []
		
		super(LinkProperty,self).__init__()
		
		# Add a reverse relation
		if self._reverse and not hasattr(self._linked_class,self._reverse):
			
			reverse_link_property = LinkProperty(self.__class__,reverse=self._name,index_property_paths=self._reverse_index_property_paths,reverse_index_property_paths=self._index_property_paths)
			reverse_link_property.setName(self._reverse)
			self._linked_class._links.append(self._reverse)
			setattr(self._linked_class,self._reverse,reverse_link_property)
		
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

	def getIndexPropertyPaths(self):

		return self._index_property_paths
	
	def getReverseIndexPropertyPaths(self):

		return self._reverse_index_property_paths

	def hasIndexes(self):

		return len(self.getIndexPropertyPaths()) > 0 or len(self.getReverseIndexPropertyPaths()) > 0

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


class EmbeddedLinkProperty(Property):
	"""
	Represents an embedded link to another document
	"""
	def __init__(self,linked_class,**kwargs):
		"""
        Args:
			linked_class (Document class): The Document class to create a link to
			
        Kwargs:
			default (Document): Default value
			required (bool): Is this a required (compulsory) property
		"""
		
		self._linked_class = linked_class
		
		# Check the linked class is a subclass of basedocument
		if not issubclass(self._linked_class,Document):
			raise ValidationError("Linked class must be a subclass of Document")
		
		super(EmbeddedLinkProperty, self).__init__(**kwargs)
	
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
		elif isinstance(value,basestring):
			instance._property_values[self._name]._id = value
		elif value:
			raise ValidationError("Not an instance of a linked class or an _id")
	
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

class BasicLock(object):
	"""
	A basic single process only lock for single threaded access to particular documents
	"""
	main_lock = threading.RLock()
	document_locks = weakref.WeakValueDictionary()
	
	def __init__(self,document_ids):
		self._document_ids = sorted(document_ids)
		self._document_locks = None
		
	def __enter__(self):
		
		# Aquire main lock whilst checking if per document locks exist
		with BasicLock.main_lock:
			self._document_locks = [BasicLock.document_locks.setdefault(document_id, threading.RLock()) for document_id in self._document_ids]
		
		# Now try and aquire locks (done in a sorted way to avoid deadlocks)
		for document_lock in self._document_locks:
			document_lock.acquire()
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		
		# Release lock (in reverse order to aquire)
		for document_lock in reversed(self._document_locks):
			document_lock.release()
		
		if exc_type is not None:
			# Exception occurred
			return False # Will raise the exception
		
		# All Ok
		return True

class Session(object):
	"""
	A couchdb server session
	"""
	def __init__(self,url,username=None,password=None,Lock=BasicLock):
		
		# Url of the couchdb server
		self._url = url
		
		# The lock class
		self._Lock = Lock
		
		# Create a session to deal with subsequent requests
		self._database_session = requests.Session()
		
		# If username and password passed in then try and login
		if username and password:
			
			# Login with basic auth first, this issues a cookie which is then used for each subsequent call
			r = self._database_session.post("%s/_session" % (self._url), data={"name": username,"password": password}, auth=(username, password))
			
			if r.status_code != 200:
				
				raise Exception(r.json())
		
	def createDatabase(self,database_name):
		
		# TODO check the database name is valid
		database_url = "%s/%s/" % (self._url, database_name)
		r = self._database_session.put(database_url)
		
		if r.status_code == 201:
			return Database(database_url,self._database_session, self._Lock)
		else:
			raise Exception(r.json())
		
	def getDatabase(self,database_name):
		
		database_url = "%s/%s/" % (self._url, database_name)
		r = self._database_session.get(database_url)
		
		if r.status_code == 200:
			return Database(database_url, self._database_session, self._Lock, info=r.json())
		else:
			raise Exception(r.json())
	
	def databaseExists(self,database_name):
		
		database_url = "%s/_all_dbs" % (self._url)
		r = self._database_session.get(database_url)
		
		if r.status_code == 200:
			return True if database_name in r.json() else False
		else:
			raise Exception(r.json())
	
	def deleteDatabase(self,database_name):
		
		database_url = "%s/%s/" % (self._url, database_name)
		r = self._database_session.delete(database_url)
		
		if r.status_code != 200:
			raise Exception(r.json())


class Database(object):
	"""
	Represents a couchdb database
	"""
	def __init__(self,database_url,database_session, Lock, info = None):
		self._database_url = database_url
		self._database_session = database_session
		self._Lock = Lock
		self._info = info
		
	def getUrl(self):
		return self._database_url
	
	# Add single document
	def add(self,document):
		
		data = json.dumps(document.instanceToDict())
		
		r = self._database_session.put("%s/%s" % (self._database_url,document._id),data=data)
		
		if r.status_code == 201:
			document._rev = r.json()["rev"]		
		else:
			raise Exception(r.json())
		
		return document
	
	# Updates a document
	def update(self,document):
		
		# Lock the document whilst updating
		with self._Lock(document._id):
			
			data = json.dumps(document.instanceToDict())
			
			r = self._database_session.put("%s/%s" % (self._database_url,document._id),data=data)
			
			if r.status_code == 201:
				document._rev = r.json()["rev"]
			else:
				raise Exception(r.json())
			
			# If this document has linked documents with indexes must update
			if issubclass(document.__class__, Document) and document.__class__.hasLinksWithIndexes():
				
				self._updateLinkIndexes(document)

			return document
	
	# Get single document
	def get(self,_id,rev=None,as_json=False):
		
		params = {}
		if rev:
			params = {"rev" : rev}
		
		r = self._database_session.get("%s/%s" % (self._database_url,_id), params = params)
		
		if r.status_code == 200:
			document_data = r.json()
			
			# See if just need to return json
			if as_json:
				return document_data
			else:
				return self._createDocument(document_data)
	
		else:
			raise Exception(r.json())
	
	# Deletes a single document
	def delete(self,document):
		
		# Lock the document whilst deleting
		with self._Lock(document._id):
			
			r = self._database_session.delete("%s/%s?rev=%s" % (self._database_url,document._id,document._rev))
			
			if r.status_code != 200:
				
				raise Exception(r.json())
			
		# If this document has linked documents must tidy up to stop orphans
		if document.__class__.hasLinks():
			
			# Delete all linkdocuments that reference the deleted document
			self.deleteAllLinks(document)
	
	# Does document id exist
	def exists(self,_id):
		
		return [_id] == self.existsMultiple([_id])
	
	# Bulk doc API used for add/update/delete multiple	
	def _bulkDocs(self,documents):
		
		docs_dict = {"docs": [document.instanceToDict() for document in documents]}
		
		headers = {"content-type": "application/json"}	
		data = json.dumps(docs_dict)
		
		r = self._database_session.post("%s/_bulk_docs" % (self._database_url),headers=headers,data=data)
		
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
		
		ok_documents = []
		failed_documents = []
		
		class_documents = {}
		
		# Must loop and place in dicts based on class
		for document in documents:

			documents = class_documents.setdefault(document.__class__,[])
			documents.append(document)
			
		for document_class in class_documents:
			
			# If no links with indexes then can safely bulk update (as no linked documents to remove)
			if not (issubclass(document.__class__, Document) and document_class.hasLinksWithIndexes()):
				
				(cls_ok_documents,cls_failed_documents) = self._bulkDocs(class_documents[document_class])
				ok_documents.extend(cls_ok_documents)
				failed_documents.extend(cls_failed_documents)
				
			else:
				
				# If links exist then must update one at a time and lock
				for document in class_documents[document_class]:
					
					try:
						
						document = self.update(document)
						ok_documents.append(document)
						
					except:
						
						failed_documents.append(document)
						
		return (ok_documents,failed_documents)
	
	# Delete multiple documents
	def deleteMultiple(self,documents):
		
		ok_documents = []
		failed_documents = []
		
		class_documents = {}
		
		# Must loop and place in dicts based on class
		for document in documents:
			
			# First mark for delete
			document.setMarkedForDelete(True)
			
			documents = class_documents.setdefault(document.__class__,[])
			documents.append(document)
			
		for document_class in class_documents:
			
			# If no links then can safely bulk delete (as no linked documents to remove)
			if not document_class.hasLinks():
				
				(cls_ok_documents,cls_failed_documents) = self._bulkDocs(class_documents[document_class])
				ok_documents.extend(cls_ok_documents)
				failed_documents.extend(cls_failed_documents)
				
			else:
				
				# If links exist then must delete one at a time and lock
				for document in class_documents[document_class]:
					
					try:
						
						self.delete(document)
						ok_documents.append(document)
						
					except:
						
						failed_documents.append(document)
						
		return (ok_documents,failed_documents)

	# Check for existence of multiple document ids (don't want to support documents as would then have to inflate first to check existance)
	def existsMultiple(self,_ids):
		headers = {"content-type": "application/json"}	
		
		data = json.dumps({"keys":_ids})
		
		r = self._database_session.post("%s/_all_docs" % (self._database_url), headers=headers,data=data)
		
		if r.status_code == 200:
			
			_ids_that_exist = []
			for row in r.json()["rows"]:
				if not ("deleted" in row or "error" in row):
					_ids_that_exist.append(row["id"])
					
			return _ids_that_exist
		
		else:
			raise Exception(r.json())
		
	# Tries to inflate a dict of data into a Document
	def _createDocument(self,document_data):
		
		# Is this a schema bound document
		if "type_" in document_data and document_data["type_"] in BaseDocument.type_class_map:
			
			document_class = BaseDocument.type_class_map[document_data["type_"]]
			
			# Now check is the current version (or if missing means is a schema design doc)
			if "schema_version_" not in document_data or ("schema_version_" in document_data and document_data["schema_version_"] == document_class.getCurrentSchemaVersion()):
				
				# Valid document so inflate
				return document_class(document_data=document_data)
		
		# Could bind to existing schema so return as unbound document
		return 	UnboundDocument(document_data)
			
	
	# Pass a json response from a view query and inflates documents
	def _processViewResponse(self,documents_data,as_json=False,**kwargs):
		
		documents = []
		
		for row in documents_data["rows"]:
			
			if as_json and "doc" in row:
				
				documents.append(row["doc"])
				
			elif "doc" in row:
				
				documents.append(self._createDocument(row["doc"]))
			
			else:
				
				documents.append(row)
				
		return documents
	
	# Get multiple documents
	def getMultiple(self,_ids):
		
		headers = {"content-type": "application/json"}	
		data = json.dumps({"keys":_ids})
		
		r = self._database_session.post("%s/_all_docs?include_docs=true" % (self._database_url), headers=headers,data=data)
		
		if r.status_code == 200:
			
			return self._processViewResponse(r.json())
		
		else:
			raise Exception(r.json())

	
	# Add links to documents
	def addLinks(self,link_property,to_documents):
		
		# The created link documents
		link_documents = []
		
		# Get the from doc and property itself
		(from_document,link_property) = link_property
	
		# See if need to add from doc
		if not from_document.hasBeenAdded():
			from_document = self.add(from_document)
			
		# Create new link document per to document
		for to_document in to_documents:
			
			documents_to_add = []
			document_ids_to_lock = [from_document._id]
			
			# See if need add to doc or lock if already exists
			if not to_document.hasBeenAdded():
				documents_to_add.append(to_document)
			else:
				document_ids_to_lock.append(to_document._id)
		
			with self._Lock(document_ids_to_lock):
				
				# Check documents exist still (as now locked)
				if document_ids_to_lock == self.existsMultiple(document_ids_to_lock):
				
					# Check not already linked (only add if not linked already)
					existing_links = self.getLinks((from_document,link_property), to_document._id)		
					if len(existing_links) == 0:
						
						# Now create link documents
						link_document = _LinkDocument()
						link_document.name = link_property.getName()
						link_document.reverse_name = link_property.getReverse()
						link_document.from_id = from_document._id
						link_document.from_type = from_document.type_
						link_document.to_id = to_document._id
						link_document.to_type = to_document.type_

						# Add indexes if present
						for index_property_path in link_property.getIndexPropertyPaths():

							(property_exists,property_value) = to_document.getPropertyValueByPath(index_property_path)
							if property_exists:
								link_document.indexes[index_property_path] = property_value

						# Add reverse indexes if present
						for reverse_index_property_path in link_property.getReverseIndexPropertyPaths():

							(property_exists,property_value) = from_document.getPropertyValueByPath(reverse_index_property_path)
							if property_exists:
								link_document.reverse_indexes[reverse_index_property_path] = property_value
							
						# Add documents to database
						documents_to_add.append(link_document)
						
						# Add to database
						link_documents.extend(self.addMultiple(documents_to_add))
		
		return link_documents
	
	# Add linked document
	def addLink(self,link_property,to_document):
		
		return self.addLinks(link_property, [to_document])
	
	# Get linked documents
	def getLinks(self,link_property,start_key=None,limit=None,as_json=False):
		
		# Get the from doc and property itself
		(from_document,link_property) = link_property
		
		start_key = [from_document._id,link_property.getName(),start_key] if start_key else [from_document._id,link_property.getName()]
		end_key = [from_document._id,link_property.getName(),{}]
		
		params = {
			"include_docs" : True,
			"startkey" : json.dumps(start_key),
			"endkey" : json.dumps(end_key)
		}
	
		if limit:
			params["limit"] = limit
			
		r = self._database_session.get("%s/_design/_linkdocument/_view/links_by_name" % (self._database_url), params = params)
		
		if r.status_code == 200:
		
			return self._processViewResponse(r.json(),as_json)
		
		else:
		
			raise Exception(r.json())

	# Get the linked documents using index
	def getLinksByIndex(self,link_property,index_property_path,index_property_value,start_key=None,limit=None,as_json=False):

		# Get the from doc and property itself
		(from_document,link_property) = link_property
		
		start_key = [from_document._id,link_property.getName(),index_property_path,index_property_value,start_key] if start_key else [from_document._id,link_property.getName(),index_property_path,index_property_value]
		end_key = [from_document._id,link_property.getName(),index_property_path,index_property_value,{}]
		
		params = {
			"include_docs" : True,
			"startkey" : json.dumps(start_key),
			"endkey" : json.dumps(end_key)
		}
	
		if limit:
			params["limit"] = limit
			
		r = self._database_session.get("%s/_design/_linkdocument/_view/links_by_indexes" % (self._database_url), params = params)
		
		if r.status_code == 200:

			return self._processViewResponse(r.json(),as_json)
		
		else:
		
			raise Exception(r.json())
	
	# Delete a linked document
	def deleteLink(self,link_property,to_document):
		
		self.deleteLinks(link_property,[to_document])
	
	# Delete many linked documents
	def deleteLinks(self,link_property,to_documents):
		
		# Get the from doc and property itself
		(from_document,link_property) = link_property
		
		# Lock the affected documents
		document_ids_to_lock = [from_document._id]
		
		# Build the keys
		_ids = []
		for to_document in to_documents:
			_ids.append([from_document._id,link_property.getName(),to_document._id])
			document_ids_to_lock.append(to_document._id)
			
		headers = {"content-type": "application/json"}
		
		params = {
			"include_docs" : True
		}
			
		data = {"keys":_ids}
		
		# Fetch the link docs
		r = self._database_session.post("%s/_design/_linkdocument/_view/by_name" % (self._database_url), headers=headers, params=params, data=json.dumps(data))

		if r.status_code == 200:

			# Turn into docs (TODO just need id so add a deleteMultipleByIds) 
			documents_to_delete = self._processViewResponse(r.json(),False)
			
			# Lock on the id's to stop links being added whilst delete is happening
			with self._Lock(document_ids_to_lock):
			
				# Finally delete the documents
				return self.deleteMultiple(documents_to_delete)
		
		else:
		
			raise Exception(r.json())	

	# For a given document this returns all the linked documents
	def deleteAllLinks(self,from_document):
		
		headers = {"content-type": "application/json"}
		
		params = {
			"include_docs" : True
			
		}

		data = {"key" : from_document._id}

		# Fetch the link docs
		r = self._database_session.post("%s/_design/_linkdocument/_view/by_id" % (self._database_url), headers=headers, params=params,  data=json.dumps(data))

		if r.status_code == 200:

			# Turn into docs (TODO just need id so add a deleteMultipleByIds) 
			documents_to_delete = self._processViewResponse(r.json(),False)
			
			# Lock on the id's to stop links being added whilst delete is happening
			with self._Lock([from_document._id]):
			
				# Finally delete the documents
				return self.deleteMultiple(documents_to_delete)
		
		else:
		
			raise Exception(r.json())

	# For a given document that has links, update the indexes on the LinkDocuments to reflect document values
	def _updateLinkIndexes(self,document):
		
		headers = {"content-type": "application/json"}
		
		params = {
			"include_docs" : True
		}

		data = {"key" : document._id}

		# Fetch the link docs
		r = self._database_session.post("%s/_design/_linkdocument/_view/by_id" % (self._database_url), headers=headers, params=params,  data=json.dumps(data))

		if r.status_code == 200:
			
			# Turn into docs
			link_documents = self._processViewResponse(r.json(),False)
			
			# Updates index dict values
			def update_index_dict(document,index_dict):

				updated = False

				for index_property_path in index_dict:
					
					# Get the correct property value
					(property_exists,property_value) = document.getPropertyValueByPath(index_property_path)

					if property_exists:

						# See if value is different to index
						if index_dict[index_property_path] != property_value:
							updated = True 
							index_dict[index_property_path] = property_value
				
					else:
					
						# If can't find the property then delete the index as schema must have changed
						del index_dict[index_property_path]

				return updated

			# Loop over link documents update indexes
			link_documents_to_update = []
			
			for link_document in link_documents:
				
				if link_document.to_id == document._id:
					
					# Normal index
					if update_index_dict(document,link_document.indexes):
						
						link_documents_to_update.append(link_document)

				elif link_document.from_id == document._id:
					
					# Reverse index
					if update_index_dict(document,link_document.reverse_indexes):
						
						link_documents_to_update.append(link_document)

			# If any documents need updating do
			if len(link_documents_to_update) > 0:
				
				self.updateMultiple(link_documents_to_update)

		else:
		
			raise Exception(r.json())

	# Loops over document classes and creates their schema's and if changed updates schema version and design docs for indexes
	def sync(self):
		
		# Loop each document class
		for document_class_name in BaseDocument.type_class_map:
			
			document_class = BaseDocument.type_class_map[document_class_name]
			
			# Don't sync design documents and system documents (seperate process for them)
			if not issubclass(document_class, DesignDocument) and document_class not in [BaseDocument,Document]:
				
				saved_schema_design_document = None
				
				try:
					
					# Try and get
					saved_schema_design_document = self.get(document_class.getSchemaDesignDocumentId(),as_json=True)
					
					# Got this far so must compare to see if it needs updating
					current_schema_design_document = document_class.getSchemaDesignDocument()
					
					# Set the _rev and version properties so like for like comparison
					current_schema_design_document._rev = saved_schema_design_document["_rev"]
					current_schema_design_document.version = saved_schema_design_document["version"]
					
					update = False
					
					# Compare saved schema to see if need to update version
					if current_schema_design_document.schema != saved_schema_design_document["schema"]:
						current_schema_design_document.version = saved_schema_design_document["version"] + 1
						update = True
						
					# See if more views/indexes have been added (e.g. not affecting the schema version)
					elif json.dumps(current_schema_design_document.instanceToDict()) != json.dumps(saved_schema_design_document):
						update = True
					
					if update:
						saved_schema_design_document = self.update(current_schema_design_document)
					else:
						saved_schema_design_document = current_schema_design_document
	
				# Add
				except Exception as e:
					
					saved_schema_design_document = self.add(document_class.getSchemaDesignDocument())
					
				# Set the schema version for document class
				document_class.setCurrentSchemaVersion(saved_schema_design_document.version)
				
			# Check design documents and see if they have fixed id's...if so check for changes and sync if needed
			elif issubclass(document_class, DesignDocument) and document_class.hasFixedId():
				
				current_design_document = document_class()
				
				try:
					
					saved_design_document = self.get(current_design_document._id)
					current_design_document._rev = saved_design_document._rev
	
					# Compare with saved (also check for unknown properties e.g. things in the doc that aren't in the schema)
					if json.dumps(current_design_document.instanceToDict()) != json.dumps(saved_design_document.instanceToDict()) > 0:
						
						saved_design_document = self.update(current_design_document)
				
				except ValidationError:
					
					# Ok doc exists but couldn't create class so just grab document (TODO this is inefficient but only happens when syncing meh)
					saved_design_document_json = self.get(current_design_document._id,as_json=True)
					current_design_document._rev = saved_design_document_json["_rev"]
					saved_design_document = self.update(current_design_document)
					
				except Exception:
					
					# Doc doesn't exist so first sync so just add
					saved_design_document = self.add(current_design_document)
				
	
	# Gets the documents by view. Passed in either a view property of Document class or design_document_id and document class
	def getByView(self,view_property=None,view_name=None,design_document_id=None,**kwargs):
			
		# A view property as defined on a Document or DesignDocument
		if view_property:
		
			# Get the parent class containing the property
			view_parent_class = view_property.getParent()
			
			# What type of view property is this a) On a Document class, b) On a Design Document class
			if issubclass(view_parent_class, DesignDocument):
				
				# Check for id arg
				if not (view_parent_class.hasFixedId() or design_document_id):
					raise Exception("Design document doesn't have a fixed id and design document id missing in args")
				elif view_parent_class.hasFixedId():
					design_document_id = view_parent_class.getFixedId()
	
				# Set the views url
				url = "%s%s/_view/%s" % (self._database_url, design_document_id, view_property.getName())
				
			else:
	
				url = "%s%s/_view/%s" % (self._database_url, view_parent_class.getSchemaDesignDocumentId(), view_property.getName())
		
		# Direct access to the view
		elif view_name and design_document_id:
			
			url = "%s%s/_view/%s" % (self._database_url, design_document_id, view_name)
		
		else:
			
			raise Exception("View property or view name and design document id missing in args")
		
		# Response type
		headers = {"content-type": "application/json"}	
		
		# The params on the url (only include docs if not a reduce)
		params = {}
		if not ("group" in kwargs or "reduce" in kwargs or "include_docs" in kwargs):
			params["include_docs"] = True
			
		for optional_param_arg in ["key","limit","skip","startkey_docid","endkey_docid","descending","group","group_level"]:
			if optional_param_arg in kwargs and kwargs[optional_param_arg]:
				params[optional_param_arg] = json.dumps(kwargs[optional_param_arg])
		
		# The data in the post body
		data = {}
		for optional_data_arg in ["keys","startkey","endkey"]:
			if optional_data_arg in kwargs and kwargs[optional_data_arg]:
				data[optional_data_arg] = kwargs[optional_data_arg]
				
		# Do the post
		r = self._database_session.post(url, headers=headers,params=params, data=json.dumps(data))
	
		if r.status_code == 200:
			
			return self._processViewResponse(r.json(),**kwargs)
		
		else:

			raise Exception(r.json())
	
	# Gets the documents by index
	def getByIndex(self,index_property,**kwargs):
		
		# Get the parent document class from the property
		document_class = index_property.getParent()
		
		# Must prefix the passed in key with the indexes name (multiple values)
		if "keys" in kwargs:
			new_keys = []
			for key in kwargs["keys"]:
				if not isinstance(key,list):
					key = [key]
				key.insert(0,index_property.getName())
				new_keys.append(key)
			kwargs["keys"] = new_keys
			
		# Must prefix the passed in key with the indexes name (single value)
		for key_arg in ["key","startkey","endkey"]:
			
			# If key, startkey or endkey then put into a list
			if key_arg in kwargs and not isinstance(kwargs[key_arg],list):
				kwargs[key_arg] = [kwargs[key_arg]]
				
			if key_arg in kwargs:
				kwargs[key_arg].insert(0,index_property.getName())
			
		return self.getByView(view_name="indexes_", design_document_id=document_class.getSchemaDesignDocumentId(),**kwargs)
	
		

class Index(object):
	"""
	Used to create a view that allows documents to queried by properties of the class
	"""
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
	
	# Create the view map function at runtime
	def getJSEmitStatement(self):
		
		emit_keys = (self._name,) + self._property_paths
		mask_string = "'%s'" + (",%s" * len(self._property_paths))
		emit_string = "emit([" + mask_string + "],doc);"
		
		return emit_string % emit_keys


class View(object):
	"""
	Represents a view
	"""
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



def _id(id):
	"""
	Decorator to set fixed id for a document class e.g. singleton documents. Decorated design document classes will be synced automatically when Database.sync() is called.
	"""
	def decorator(document_class):
		document_class._fixed_id = id
		return document_class
	return decorator


class BaseDocumentMetaClass(SchemaMetaClass):
	""" 
	Metaclass for basedocument
	"""
	def __new__(cls, classname, bases, classDict):

		# Create the new document class
		base_document_class = SchemaMetaClass.__new__(cls, classname, bases, classDict)
		
		# Store in map (this is actually a static)
		base_document_class.type_class_map[classname.lower()] = base_document_class
		
		# Extend statics
		_views = []
		for base in bases:
			if hasattr(base,"_views"):
				_views.extend(base._views)
		
		# Views can be added to the Document subclasses (actually added to their schema design document) or to design documents...hence why in BaseDocumentMetaClass
		
		# Iterate through the new class' __dict__ and update all recognised view names
		for name, attr in classDict.iteritems():
			
			if isinstance(attr, View):
				
				# Store the name of the index in the descriptor
				attr.setName(name)
				
				# Store the parent class in the property
				attr.setParent(base_document_class)
				
				# Append the name of the index to class var
				_views.append(name)
		
		# Set class property
		base_document_class._views = _views
		
		
		return base_document_class



class BaseDocument(Schema):
	"""
	The base class that represents a schema bound document within couchdb
	"""
	__metaclass__ = BaseDocumentMetaClass
	
	# Static to store a mapping between type and class
	type_class_map = {}
	
	# The properties
	_id = StringProperty(required=True)
	_rev = StringProperty(required=True)
	type_ = StringProperty(required=True)
	
	def __init__(self,document_data=None):
		
		super(BaseDocument,self).__init__()
		
		# Set the classname as the type if not got a default set
		self.type_ = self.__class__.__name__.lower()
		
		# See if data passed in
		if document_data == None:
			
			# Set id if not passed in
			self._id = uuid.uuid1().hex
	
		else:
			
			self.instanceFromDict(document_data)
			
		# Store special flag for deletion
		self._marked_for_delete = False
	
	
	def instanceToDict(self):
		""" Convert the document class object to a dict """
		
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
	
	def __eq__(self,other):
		
		return self.instanceToDict() == other.instanceToDict()
	
	# Has the document been added to the database yet?
	def hasBeenAdded(self):
		
		return not (self._rev == None)
	
	# Mark this document for delete
	def setMarkedForDelete(self,marked_for_delete=True):
		
		self._marked_for_delete = marked_for_delete


class DesignDocument(BaseDocument):
	"""
	Base class that design document classes should extend
	"""

	def __init__(self,document_data=None):
		
		# Used to store actual values of views (can't store in descriptor objects as they are static)
		self._view_values = {}
		
		super(DesignDocument,self).__init__(document_data=document_data)
		
		# Use fixed id if set
		if hasattr(self,"_fixed_id"):
			self._id = self._fixed_id
	
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
		
		if isinstance(dict_data,dict):
			
			# Loop known views
			for view_name in self.__class__._views:
				
				if "views" in dict_data and view_name in dict_data["views"]:
					
					setattr(self,view_name,dict_data["views"][view_name])
				
				elif "views" in dict_data and view_name not in dict_data["views"]: 

					raise ValidationError("View %s is required but not present" % view_name)
			
			# Remove from dict for validation for extraneous properties
			if "views" in dict_data:
				del dict_data["views"]
		
		super(DesignDocument,self).instanceFromDict(dict_data)
	
	# Has the design doc been set an id as part of the class definition (most will have)
	@classmethod
	def hasFixedId(cls):
		
		return hasattr(cls,"_fixed_id") and cls._fixed_id != None
	
	# Return the fixed id
	@classmethod
	def getFixedId(cls):
		
		return cls._fixed_id
					
	
	
"""
Design document containing schema and indexes view
"""
class _SchemaDesignDocument(DesignDocument):

	# The current schema of the document
	schema = StringProperty()
	version = NumberProperty(default=0)
	
	# The indexes view
	indexes_ = View()


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
		
		_links = []
		for base in bases:
			if hasattr(base,"_links"):
				_links.extend(base._links)

		# Iterate through the new class' __dict__ and update all recognised index names
		for name, attr in classDict.iteritems():
			
			if isinstance(attr, Index):
				
				# Store the name of the index in the descriptor
				attr.setName(name)
				
				# Store the parent class in the property
				attr.setParent(document_class)
				
				# Append the name of the index to class var
				_indexes.append(name)
			
			# Store whether class contains any Link properties
			if isinstance(attr,LinkProperty):
				
				_links.append(name)
		
		# Set class property
		document_class._indexes = _indexes
		document_class._links = _links
		
		# Loop over the view properties and copy them into the new class
		schema_design_document_class_views = {}
		for view_name in document_class._views:
			schema_design_document_class_views[view_name] = copy.deepcopy(getattr(document_class,view_name))
		
		# Create a new class to represent the schema design document	
		document_class._schema_design_document_class = type('_SchemaDesignDocument%s' % (classname), (_SchemaDesignDocument,), schema_design_document_class_views)

		return document_class



class Document(BaseDocument):
	"""
	Base class that your model classes should extend
	"""
	
	__metaclass__ = DocumentMetaClass
	
	# Static map to store the current version
	_current_schema_version = {}
	
	# Used to keep track of which schema version created this
	schema_version_ = NumberProperty(required=True)
	
	def __init__(self,document_data=None):
		
		super(Document,self).__init__(document_data=document_data)
		
		# See if data passed in
		if document_data == None:
		
			# Store the rev of the current schema that has been used to create this document
			self.schema_version_ = self.getCurrentSchemaVersion()
			
	# Get the current version for this class
	@classmethod
	def getCurrentSchemaVersion(cls):	
		
		if cls.__name__.lower() in Document._current_schema_version:
			return Document._current_schema_version[cls.__name__.lower()]
		else:
			return None
	
	# Set the current version for this class
	@classmethod
	def setCurrentSchemaVersion(cls,schema_version):	
		
		Document._current_schema_version[cls.__name__.lower()] = schema_version
	
	# Get the document id
	@classmethod
	def getSchemaDesignDocumentId(cls):
		
		return "_design/_schema_%s" % (cls.__name__.lower())
	
	# Schema design doc contains index and link views
	@classmethod
	def getSchemaDesignDocument(cls):
		
		# Create an instance of the schema document
		schema_design_document = cls._schema_design_document_class()
		schema_design_document._id = cls.getSchemaDesignDocumentId()
		
		# Set the schema
		schema_design_document.schema = json.dumps(cls.schemaToDict())
		
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
		
		else:
			
			# Set to blank function
			schema_design_document.indexes_["map"] = "function(doc){}"
		
		return schema_design_document
	
	@classmethod
	def hasLinks(cls):
		
		return len(cls._links) > 0

	@classmethod
	def hasLinksWithIndexes(cls):
		
		for link_property in cls._links:
			
			if getattr(cls,link_property).hasIndexes():
				return True

		return False
			
"""
Used for unbound documents e.g. documents that aren't compliant with a schema
"""			
class UnboundDocument(dict):
	pass


"""
Used to store relationship between documents
"""
class _LinkDocument(Document):
	
	name = StringProperty()
	reverse_name = StringProperty()
	from_type = StringProperty()
	to_type = StringProperty()
	from_id = StringProperty()
	to_id = StringProperty()

	def __init__(self,document_data=None):
		
		super(_LinkDocument,self).__init__(document_data=document_data)

		# Used to store secondary indexes on the linked document (to allow for quicker return of links)
		self.indexes = getattr(self,"indexes",{})
		self.reverse_indexes = getattr(self,"reverse_indexes",{})

	# Overridden so that indexes added to the dict 
	def instanceToDict(self):

		document_data = super(_LinkDocument,self).instanceToDict()
		document_data["indexes"] = self.indexes
		document_data["reverse_indexes"] = self.reverse_indexes
		
		return document_data

	# Overridden so that indexes can be taken out the dict
	def instanceFromDict(self,dict_data):
		

		if "indexes" in dict_data and "reverse_indexes" in dict_data:
			self.indexes = dict_data["indexes"]
			self.reverse_indexes = dict_data["reverse_indexes"]
			del dict_data["indexes"]
			del dict_data["reverse_indexes"]
		
		super(_LinkDocument,self).instanceFromDict(dict_data)
	
	
"""
Design document dealing with links
"""
@_id("_design/_linkdocument")
class _LinkDesignDocument(DesignDocument):

	# Returns the actual links documents by id (used in document delete to remove all linked documents)
	by_id = View({
		"map" :(
			"function(doc) {"
				"if(doc.type_=='_linkdocument') {"
					"emit(doc.from_id,null);"
					"emit(doc.to_id,null);"
				"}"
			"}"
		)
	})

	# Returns the actual link documents (used mostly in deleteLinks)
	by_name = View({
		"map" :(
			"function(doc) {"
				"if(doc.type_=='_linkdocument') {"
					"emit([doc.from_id,doc.name,doc.to_id],{'_id': doc._id});"
					"emit([doc.to_id,doc.reverse_name,doc.from_id],{'_id': doc._id});"
				"}"
			"}"
		)
	})
	
	# Returns the linked docs
	links_by_name = View({
		"map" :(
			"function(doc) {"
				"if(doc.type_=='_linkdocument') {"
					"emit([doc.from_id,doc.name,doc.to_id],{'_id': doc.to_id});"
					"emit([doc.to_id,doc.reverse_name,doc.from_id],{'_id': doc.from_id});"
				"}"
			"}"
		)
	})

	# Returns the linked docs by indexes
	links_by_indexes = View({
		"map" :(
			"function(doc) {"
				"if(doc.type_=='_linkdocument') {"
					"for(property_path in doc.indexes) {"
						"emit([doc.from_id,doc.name,property_path,doc.indexes[property_path],doc.to_id],{'_id': doc.to_id});"
					"}"
					"for(property_path in doc.reverse_indexes) {"
						"emit([doc.to_id,doc.reverse_name,property_path,doc.reverse_indexes[property_path],doc.from_id],{'_id': doc.from_id});"
					"}"
				"}"
			"}"
		)
	})		