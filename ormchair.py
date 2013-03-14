'''
Created on 24 Jan 2013

@author: will
'''
import requests
import uuid
import json

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
			if self._name in instance._propertyValues:
				return instance._propertyValues[self._name]
			else:
				return None
	
	def __set__(self, instance, value):
		
		if instance:
			
			if self._validate(value):
				instance._propertyValues[self._name] = value
	
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
				
		return type.__new__(cls, classname, bases, classDict)

"""
Mapped to a class
"""
class Schema(object):
	
	# Set the name on all the descriptors within this class
	__metaclass__ = SchemaMetaClass
	
	# Is this a root schema or subschema
	_is_root = True
	
	def __init__(self,*args,**kwargs):
		
		# Used to store actual values of properties (can't store in descriptor objects as they are static)
		self._propertyValues = {}

		# Set parent and defaults on properties
		for property_name in self._properties:
			
			# Defaults
			default_value = getattr(self.__class__,property_name).getDefaultValue()
			setattr(self,property_name,default_value)
	
	# Set the values of the schema from a dict	
	def instanceFromDict(self,dict_data):
		
		if isinstance(dict_data,dict):
			for key in dict_data:
				if key in self._properties:
					setattr(self,key,dict_data[key])
				else:
					raise ValidationError("No property %s exists" % key)
	
	# Export the schemas values as a basic dict
	def instanceToDict(self):
		
		dict_data = {}
		
		# Loop over properties
		for property_name in self._properties:
			
			dict_data[property_name] = getattr(self.__class__,property_name).instanceToDict(self)
		
		return dict_data
	
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

			# Return instanc of subclas
			return instance._propertyValues[self._name]
	

	def __set__(self, instance, value):
		
		self._checkForPropertyValue(instance)
		
		instance._propertyValues[self._name].instanceFromDict(value)
	
	# Make sure property value has been set	
	def _checkForPropertyValue(self,instance):
		# Check to see if property exists on instance
		if self._name not in instance._propertyValues:
				
			# Create instance of schema subclass
			instance._propertyValues[self._name] = self._cls()
	
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
	
	def __init__(self, itr, cls): 
		
		self._cls = cls
		
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
		list_instance = self._cls(is_root=False)
		
		# Populate from dict (and thus validate)
		list_instance.instanceFromDict(value)
		
		return list_instance
	
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
	
	def __init__(self,*args,**kwargs):
		
		self._options = kwargs.pop('_options', None)
		
		# Create a new subclass of Schema based on passed in items dict
		kwargs["_is_root"] = False
		self._cls = type('SchemaSubClass', (Schema,), kwargs)
		
		super(ListProperty, self).__init__(self,*args,**kwargs)
	
	# Get
	def __get__(self, instance, owner):
		
		if instance is None:
			# Return descriptor
			return self
		else:
			
			# If first time accessed set default
			if self._name not in instance._propertyValues:
				
				# Create instance of schema subclass
				self.__set__(instance,[])
				
			# Return instance of subclass
			return instance._propertyValues[self._name]
	
	# Set
	def __set__(self, instance, value):
		
		if value == None:
			value = []
		
		# Store a dictpropertylist on the instance
		instance._propertyValues[self._name] = DictPropertyList(value,self._cls)
		

	# Get the object as JSON
	def instanceToDict(self,instance):
		
		# Empty array
		list_data = []
		
		# Loop over dictpropertlist
		for item in self.__get__(instance,None):
		
			list_data.append(item.instanceToDict())
				
		return list_data
	
	def schemaToDict(self):
		
		return {
			"items" : self._cls.schemaToDict()
		}


"""
Property to link to other schemas
"""
class LinkProperty(Property):
	
	def __init__(self,linked_class,*args,**kwargs):
		
		self._linked_class = linked_class
		self._type = kwargs.pop('type', "one_to_one")
		self._reverse = kwargs.pop('reverse', None)
		
		super(LinkProperty,self).__init__(*args,**kwargs)
		
		# Add a reverse relation
		if self._reverse and not hasattr(self._linked_class,self._reverse):
			
			# Add reverse type
			if self._type in ["one_to_one","one_to_many"]:
				reverse_type = "one_to_one"
			else:
				reverse_type = "many_to_many"
			
			setattr(self._linked_class,self._reverse,LinkProperty(self.__class__,type=reverse_type,reverse=self._name))
		
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
			if instance._propertyValues[self._name]._inflated:
				return instance._propertyValues[self._name]._document
			else:
				# Return id
				return instance._propertyValues[self._name]._id
	

	def __set__(self, instance, value):
		
		self._checkForPropertyValue(instance)
		
		# If value is a an instance of linked class then this is the data to inflate this property else it's just an id
		if isinstance(value,self._linked_class):
			instance._propertyValues[self._name]._inflated = True
			instance._propertyValues[self._name]._document = value
			instance._propertyValues[self._name]._id = value._id
		else:
			instance._propertyValues[self._name]._id = value
	
	# Make sure property value has been set	
	def _checkForPropertyValue(self,instance):
		# Check to see if property exists on instance
		if self._name not in instance._propertyValues:
				
			instance._propertyValues[self._name] = EmbeddedLink()
			
	def instanceToDict(self,instance):
		
		if instance:
			return instance._propertyValues[self._name]._id
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
		
		r = requests.put("%s/%s" % (self._database_url,document._id),data=document.toJson())
		
		if r.status_code == 201:
			document._rev = r.json()["rev"]		
		else:
			raise Exception(r.json())
		
		return document
	
	# Updates a document
	def update(self,document):
		
		r = requests.put("%s/%s" % (self._database_url,document._id),data=document.toJson())
		if r.status_code == 201:
			document._rev = r.json()["rev"]
		else:
			raise Exception(r.json())
		
		return document
	
	# Get single document
	def get(self,_id,rev=None):
		
		params = {}
		if rev:
			params = {"rev" : rev}
		
		r = requests.get("%s/%s" % (self._database_url,_id), params = params)
		
		if r.status_code == 200:
			document_data = r.json()
			
			# Get the correct class (if not fall back to document) 
			if document_data["type_"] in type_class_map:
				document_class = type_class_map[document_data["type_"]]
			else:
				document_class = Document
			
			return document_class(document_data=document_data)
		
		else:
			raise Exception(r.json())
	
	
	# Bulk doc API used for add/update/delete multiple	
	def _bulkDocs(self,documents):
		
		documents_json = ",".join([document.toJson() for document in documents])
		
		headers = {"content-type": "application/json"}	
		data = ('{"docs": [%s]}') % documents_json
		
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
	
	# Get multiple documents
	def getMultiple(self,_ids):
		
		headers = {"content-type": "application/json"}	
		data = json.dumps({"keys":_ids})
		
		r = requests.post("%s/_all_docs?include_docs=true" % (self._database_url), headers=headers,data=data)
		
		if r.status_code == 200:
			documents = []
			documents_data = r.json()
			
			for row in documents_data["rows"]:
				
				# Get the correct class (if not fall back to document) 
				if row["doc"]["type_"] in type_class_map:
					document_class = type_class_map[row["doc"]["type_"]]
				else:
					document_class = Document
			
				documents.append(document_class(document_data=row["doc"]))
			
			return documents
		
		else:
			raise Exception(r.json())
	
	
	# Add links to documents
	def addLinks(self,link_property_tuple,to_documents):
		
		# Get the from doc and property itself
		(from_document,link_property) = link_property_tuple
		
		# Check to make sure documents have been added to the db
		documents_to_add = []
		if not from_document.hasBeenAdded():
			documents_to_add.append(from_document)
			
		# Create new link document per to document
		for to_document in to_documents:
			if not to_document.hasBeenAdded():
				documents_to_add.append(to_document)
		
			# Now create link documents
			to_link_document = LinkDocument()
			to_link_document.name = link_property.getName()
			to_link_document.from_id = from_document._id
			to_link_document.from_type = from_document.type_
			to_link_document.to_id = to_document._id
			to_link_document.to_type = to_document.type_
			
			from_link_document = LinkDocument()
			from_link_document.name = link_property.getReverse()
			from_link_document.from_id = to_document._id
			from_link_document.from_type = to_document.type_
			from_link_document.to_id = from_document._id
			from_link_document.to_type = from_document.type_
			
			# Add documents to database
			documents_to_add.extend([to_link_document,from_link_document])
		
		return self.addMultiple(documents_to_add)
	
	# Add link to document
	def addLink(self,link_property_tuple,to_document):
		
		return self.addLinks(link_property_tuple, [to_document])
	
	# Takes a list of document classes and creates their schema's and if changed updates schema version and design docs 
	def syncClasses(self,document_classes):
		pass	
		

""" 
Metaclass to register the document class with a type
"""
class DocumentMetaClass(SchemaMetaClass):
	
	def __new__(cls, classname, bases, classDict):
		
		type_class = SchemaMetaClass.__new__(cls, classname, bases, classDict)
		
		# Store in map
		type_class_map[classname.lower()] = type_class
		
		return type_class


"""
The main class to extend. Represents a couchdb schema bound document
"""
class Document(Schema):
	
	__metaclass__ = DocumentMetaClass
	
	# The properties
	_id = StringProperty(required=True)
	_rev = StringProperty(required=True)
	type_ = StringProperty(required=True)
	
	def __init__(self,document_data=None):
		
		Schema.__init__(self)
		
		# See if data passed in
		if document_data == None:
			self._id = uuid.uuid1().hex
			self.type_ = self.type_ if self.type_ else self.__class__.__name__.lower()
		else:
			self.instanceFromDict(document_data)
			
		# Store special flag for deletion
		self._marked_for_delete = False
	
	
	# Get the document as JSON
	def toJson(self):
		
		# Empty dict
		document_data = {}
		
		# See if marked for delete
		if self._marked_for_delete:
			document_data["_deleted"] = True
		
		# Loop over properties
		for property_name in self._properties:
			if not (property_name == "_rev" and self._rev == None):
				
				document_data[property_name] = getattr(self.__class__,property_name).instanceToDict(self)		
		
		return json.dumps(document_data)
	
	# Has the document been added to the database yet?
	def hasBeenAdded(self):
		
		return not (self._rev == None)
	
	# Mark this document for delete
	def setMarkedForDelete(self,marked_for_delete=True):
		
		self._marked_for_delete = marked_for_delete


"""
Used to store relationship between documents
"""
class LinkDocument(Document):
	
	type_ = StringProperty(default="_link")
	name = StringProperty()
	from_type = StringProperty()
	to_type = StringProperty()
	from_id = StringProperty()
	to_id = StringProperty()
	
	def __init__(self,*args,**kwargs):
		super(LinkDocument,self).__init__(*args,**kwargs)